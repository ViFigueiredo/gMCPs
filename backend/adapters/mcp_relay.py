"""MCP Relay — shared container mode: one container per MCP, N clients via SSE."""

import asyncio
import json
import logging
import os
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger("mcp_relay")

# ── Global registry of running relays ──────────────────────────────────
_relays: dict[str, "McpRelay"] = {}
_lock = threading.Lock()


def get_relay(mcp_name: str) -> "McpRelay | None":
    return _relays.get(mcp_name)


def list_relays() -> list["McpRelay"]:
    return list(_relays.values())


class McpRelay:
    """Manages one shared MCP container with multi-client SSE proxy.

    Usage:
        relay = McpRelay("memory", port=3100)
        relay.start()          # spawns container + SSE server
        relay.stop()           # kills container + SSE server
    """

    def __init__(self, mcp_name: str, port: int, base_port: int = 3100):
        self.mcp_name = mcp_name
        self.port = port
        self.base_port = base_port
        self.container_proc: subprocess.Popen | None = None
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._clients: list[asyncio.Queue] = []
        self._client_lock = threading.Lock()
        self._stdout_thread: threading.Thread | None = None
        self._sse_connections: list[SSEHandler] = []

    # ── Public API ──────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True

        # Spawn container
        try:
            self.container_proc = subprocess.Popen(
                ["docker", "run", "-i", "--rm", "--name", f"mcp-shared-{self.mcp_name}",
                 f"mcp/{self.mcp_name}"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            logger.error(f"mcp_relay: docker not found for {self.mcp_name}")
            self._running = False
            return

        # Thread to read stdout and push to SSE clients
        self._stdout_thread = threading.Thread(target=self._pipe_stdout, daemon=True)
        self._stdout_thread.start()

        # Start SSE HTTP server
        self._server = HTTPServer(("127.0.0.1", self.port), self._make_handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        logger.info(f"mcp_relay: {self.mcp_name} shared on :{self.port}")

        # Register globally
        with _lock:
            _relays[self.mcp_name] = self

    def stop(self):
        logger.info(f"mcp_relay: stopping {self.mcp_name}")
        self._running = False

        # Kill container
        if self.container_proc:
            try:
                self.container_proc.terminate()
                self.container_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.container_proc.kill()
            except Exception:
                pass
            self.container_proc = None

        # Stop HTTP server
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None

        # Unregister
        with _lock:
            _relays.pop(self.mcp_name, None)

        # Cleanup docker container
        subprocess.run(
            ["docker", "rm", "-f", f"mcp-shared-{self.mcp_name}"],
            capture_output=True, timeout=10
        )

        logger.info(f"mcp_relay: {self.mcp_name} stopped")

    @property
    def active_clients(self) -> int:
        return sum(1 for h in self._sse_connections if h._active)

    def to_dict(self) -> dict:
        return {
            "mcp_name": self.mcp_name,
            "port": self.port,
            "running": self._running,
            "active_clients": self.active_clients,
        }

    # ── Internal ────────────────────────────────────────────────────

    def _pipe_stdout(self):
        """Read container stdout and queue messages for all SSE clients."""
        if not self.container_proc or not self.container_proc.stdout:
            return
        try:
            for line in iter(self.container_proc.stdout.readline, b""):
                if not self._running:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                # Broadcast to all connected SSE clients
                with self._client_lock:
                    for handler in self._sse_connections:
                        try:
                            handler.send_message(text)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"mcp_relay: stdout pipe error for {self.mcp_name}: {e}")

    def _send_to_container(self, message: str):
        """Write a JSON-RPC message to the container's stdin."""
        if self.container_proc and self.container_proc.stdin:
            try:
                self.container_proc.stdin.write((message + "\n").encode("utf-8"))
                self.container_proc.stdin.flush()
            except Exception as e:
                logger.warning(f"mcp_relay: stdin write error for {self.mcp_name}: {e}")

    def _make_handler(self):
        """Factory for SSE request handler bound to this relay."""
        relay = self

        class Handler(BaseHTTPRequestHandler):
            _active = True

            def log_message(self, fmt, *args):
                pass  # suppress default HTTP logs

            def do_GET(self):
                if self.path.startswith("/sse"):
                    self._handle_sse(relay)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                parsed = urlparse(self.path)
                if parsed.path == "/message" or parsed.path == "/sse":
                    self._handle_message(relay, parsed)
                else:
                    self.send_response(404)
                    self.end_headers()

            def _handle_sse(self, r: McpRelay):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                session_id = f"{r.mcp_name}-{id(self)}"
                endpoint = f"/sse?sessionid={session_id}"
                self.wfile.write(f"event: endpoint\ndata: {endpoint}\n\n".encode())
                self.wfile.flush()

                # Register client
                with r._client_lock:
                    r._sse_connections.append(self)

                # Keep connection alive, read SSE data from container
                try:
                    while r._running and self._active:
                        time.sleep(0.1)
                        # Send keepalive
                        self.wfile.write(": keepalive\n\n".encode())
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with r._client_lock:
                        if self in r._sse_connections:
                            r._sse_connections.remove(self)

            def _handle_message(self, r: McpRelay, parsed):
                qs = parse_qs(parsed.query)
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len else ""
                if body:
                    r._send_to_container(body)
                # Respond with OK
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"jsonrpc":"2.0","result":{},"id":null}')
                self.wfile.flush()

            def send_message(self, text: str):
                """Send a message to this client's SSE stream."""
                try:
                    self.wfile.write(f"event: message\ndata: {text}\n\n".encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    self._active = False

        return Handler


# ── Helper functions ───────────────────────────────────────────────────

def start_shared_server(mcp_name: str, port: int) -> dict:
    """Start a shared relay for an MCP server. Returns relay status dict."""
    if mcp_name in _relays:
        return _relays[mcp_name].to_dict()
    relay = McpRelay(mcp_name, port)
    relay.start()
    if not relay._running:
        raise RuntimeError(f"Failed to start relay for {mcp_name}")
    return relay.to_dict()


def stop_shared_server(mcp_name: str) -> bool:
    """Stop a shared relay. Returns True if it was running."""
    relay = _relays.get(mcp_name)
    if not relay:
        return False
    relay.stop()
    return True


def get_next_port(base: int = 3100, max_port: int = 3200) -> int:
    """Find the next available port starting from base."""
    with _lock:
        used = {r.port for r in _relays.values()}
    for port in range(base, max_port + 1):
        if port not in used:
            # Quick check port isn't in use by system
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(("127.0.0.1", port))
                s.close()
                return port
            except OSError:
                continue
    raise RuntimeError("No available ports for shared relay")
