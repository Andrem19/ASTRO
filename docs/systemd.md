# systemd

This project runs directly on Linux from conda environment `astro`. The paths below are
examples; adjust them to your server.

Example unit:

```ini
[Unit]
Description=Astrology MCP Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/astrology-mcp-server
EnvironmentFile=/opt/astrology-mcp-server/.env
ExecStart=/opt/miniconda3/envs/astro/bin/python -m astrology_mcp.main
Restart=always
RestartSec=5
User=astro
Group=astro

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/astrology-mcp-server.service` with that content, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable astrology-mcp-server
sudo systemctl start astrology-mcp-server
sudo systemctl status astrology-mcp-server
```

Typical deployment commands before enabling the service:

```bash
git clone <repo-url> /opt/astrology-mcp-server
cd /opt/astrology-mcp-server
conda env create -f environment.yml
conda run -n astro python -m pip install -e .
conda run -n astro alembic upgrade head
```

Logs:

```bash
journalctl -u astrology-mcp-server -f
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Do not log full birth dates with times, full profile notes, API keys, or complete raw birth
data payloads. Application tool logs include request id, tool name, duration, status, and
error type.
