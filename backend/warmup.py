import json, urllib.request, time, os

def try_call(server, method):
    try:
        req = urllib.request.Request(f"http://localhost:3099/sse?server={server}", headers={"Authorization": "Bearer mcp-local-token"})
        with urllib.request.urlopen(req, timeout=5) as r:
            session = None
            for line in r.read().decode().split("\n"):
                if "sessionid=" in line: session = line.split("sessionid=")[-1].strip()
            if session:
                msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
                urllib.request.urlopen(f"http://localhost:3099/message?sessionid={session}", data=msg, timeout=5)
                print(f"Warmed up {server}")
    except: pass

time.sleep(5)
try_call("neon", "list_projects")
try_call("github", "list_issues")
