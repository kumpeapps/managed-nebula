[Unit]
Description=Managed Nebula Server (Docker Compose)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={{COMPOSE_WORKING_DIR}}
ExecStart=/usr/bin/docker compose {{COMPOSE_FILES_FLAGS}} -p {{COMPOSE_PROJECT_NAME}} up -d {{COMPOSE_SERVICE_NAME}}
ExecStop=/usr/bin/docker compose {{COMPOSE_FILES_FLAGS}} -p {{COMPOSE_PROJECT_NAME}} stop {{COMPOSE_SERVICE_NAME}}
ExecReload=/usr/bin/docker compose {{COMPOSE_FILES_FLAGS}} -p {{COMPOSE_PROJECT_NAME}} restart {{COMPOSE_SERVICE_NAME}}
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
