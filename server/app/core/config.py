from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "development")
    db_url: str = os.getenv("DB_URL", "sqlite+aiosqlite:///./app.db")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    ca_default_validity_days: int = int(os.getenv("CA_DEFAULT_VALIDITY_DAYS", "540"))  # 18 months
    ca_rotate_at_days: int = int(os.getenv("CA_ROTATE_AT_DAYS", "365"))  # 12 months
    ca_overlap_days: int = int(os.getenv("CA_OVERLAP_DAYS", "90"))  # 3 months

    client_cert_validity_days: int = int(os.getenv("CLIENT_CERT_VALIDITY_DAYS", "180"))  # 6 months
    client_rotate_before_days: int = int(os.getenv("CLIENT_ROTATE_BEFORE_DAYS", "90"))  # 3 months

    lighthouse_default_port: int = int(os.getenv("LIGHTHOUSE_DEFAULT_PORT", "4242"))
    server_public_url: str = os.getenv("SERVER_PUBLIC_URL", "http://localhost:8080")

    # Schema auto-sync (disabled by default; use Alembic for production)
    enable_schema_autosync: bool = os.getenv("ENABLE_SCHEMA_AUTOSYNC", "false").lower() in ("true", "1", "yes")

    # If true, users are managed externally and local add/edit/delete should be disabled
    externally_managed_users: bool = os.getenv("EXTERNALLY_MANAGED_USERS", "false").lower() in ("true", "1", "yes")
    
    # GitHub API token for accessing GitHub API (optional, but recommended for higher rate limits)
    github_token: str = os.getenv("GITHUB_TOKEN", "")


# Default Nebula version used across the application
DEFAULT_NEBULA_VERSION = "1.10.3"

settings = Settings()
