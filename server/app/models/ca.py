from sqlalchemy import String, Integer, Boolean, DateTime, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..db import Base


class CACertificate(Base):
    __tablename__ = "ca_certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    pem_cert: Mapped[bytes] = mapped_column(LargeBinary)  # PEM-encoded X.509 (placeholder for Nebula cert)
    pem_key: Mapped[bytes] = mapped_column(LargeBinary)   # PEM-encoded private key (empty if not available)
    not_before: Mapped[datetime] = mapped_column(DateTime)
    not_after: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_previous: Mapped[bool] = mapped_column(Boolean, default=False)
    # Whether this CA can be used for signing (requires private key)
    can_sign: Mapped[bool] = mapped_column(Boolean, default=True)
    # Whether to include this CA cert in generated client configs (CA bundle)
    include_in_config: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
