FROM python:3.14-slim

WORKDIR /app

# Install Node.js 22 LTS + Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && curl -fsSL https://get.docker.com | bash - \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy docker-mcp CLI plugin from host (requires Docker MCP Desktop)
COPY /usr/lib/docker/cli-plugins/docker-mcp /usr/lib/docker/cli-plugins/docker-mcp
RUN chmod +x /usr/lib/docker/cli-plugins/docker-mcp

# Copy project files
COPY . .

# Install deps
RUN pip install --no-cache-dir -r requirements.txt && \
    npm install && \
    npm run build-only

# Runtime dirs
RUN mkdir -p /root/.config/gmcp /root/.docker/mcp

# Expose ports: API 8000, Frontend 8173
EXPOSE 8000 8173

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD curl -sf http://localhost:8000/api/stats > /dev/null

CMD ["node", "bin/gmcp-web.js"]
