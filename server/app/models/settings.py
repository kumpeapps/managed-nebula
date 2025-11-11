from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lighthouse_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lighthouse_port: Mapped[int] = mapped_column(Integer, default=4242)
    lighthouse_hosts: Mapped[str] = mapped_column(String(2000), default="[]")  # JSON array of host ips
    default_groups: Mapped[str] = mapped_column(String(2000), default="[]")
    default_firewall_rules: Mapped[str] = mapped_column(String(5000), default="[]")
    default_cidr_pool: Mapped[str] = mapped_column(String(64), default="10.100.0.0/16")
    # Enable Nebula punchy (see https://nebula.defined.net/docs/config/punchy/)
    punchy_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Default Docker image for client containers
    client_docker_image: Mapped[str] = mapped_column(String(500), default="ghcr.io/kumpeapps/managed-nebula/client:latest")
    # Server URL for client docker-compose files
    server_url: Mapped[str] = mapped_column(String(500), default="http://localhost:8080")
