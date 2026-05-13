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

Tool registry check:

```bash
cd /opt/astrology-mcp-server
conda run -n astro python -c "import asyncio; from astrology_mcp.mcp_server import create_mcp_server; tools=asyncio.run(create_mcp_server().list_tools()); print('\n'.join(tool.name for tool in tools))"
```

If a tool appears in `list_supported_features` but is missing from the connected MCP
client, restart the service and refresh/reconnect that client. Some clients cache the
tool schema separately from normal tool responses.

Telegram startup notifications:

```text
ALGO_BOT=
CHAT_ID=
TELEGRAM_OUTBOX_DIR=./runtime/telegram_outbox
TELEGRAM_MAX_FILE_SIZE_MB=20
```

If both values are set in `.env`, the service sends `astro-mcp перезапущен успешно`
after ASGI startup completes and tries to send `astro-mcp неуспешный запуск: <error>`
if startup fails. The same bot token and chat id are used by the `send_telegram_message`
MCP tool. Leave either value empty to disable Telegram sending.

Do not log full birth dates with times, full profile notes, API keys, or complete raw birth
data payloads. Application tool logs include request id, tool name, duration, status, and
error type.
