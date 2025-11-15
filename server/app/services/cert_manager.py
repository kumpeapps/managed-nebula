from __future__ import annotations
from datetime import datetime, timedelta
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import tempfile
import subprocess
import os

from ..models import CACertificate, Client, ClientCertificate
from ..core.config import settings


class CertManager:
    """Nebula certificate manager using nebula-cert CLI."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_new_ca(self, name: str) -> CACertificate:
        now = datetime.utcnow()
        # nebula-cert expects Go-style durations (e.g., hours). Convert days -> hours.
        duration_hours = settings.ca_default_validity_days * 24
        duration = f"{duration_hours}h"
        with tempfile.TemporaryDirectory() as td:
            # Generate CA
            cmd = [
                "nebula-cert",
                "ca",
                "-name",
                name,
                "-duration",
                duration,
            ]
            subprocess.check_call(cmd, cwd=td)
            # Files: ca.key, ca.crt
            with open(os.path.join(td, "ca.crt"), "rb") as f:
                pem_cert = f.read()
            with open(os.path.join(td, "ca.key"), "rb") as f:
                pem_key = f.read()

        # Mark existing active as previous for overlap
        cas = (
            await self.session.execute(
                select(CACertificate).where(CACertificate.is_active == True)
            )
        ).scalars().all()
        for c in cas:
            c.is_previous = True
            c.include_in_config = True
            await self.session.flush()

        not_after = now + timedelta(days=settings.ca_default_validity_days)
        ca = CACertificate(
            name=name,
            pem_cert=pem_cert,
            pem_key=pem_key,
            not_before=now,
            not_after=not_after,
            is_active=True,
            is_previous=False,
            can_sign=True,
            include_in_config=True,
        )
        self.session.add(ca)
        await self.session.commit()
        return ca

    async def ensure_future_ca(self):
        now = datetime.utcnow()
        active_cas = (
            await self.session.execute(
                select(CACertificate).where(CACertificate.is_active == True)
            )
        ).scalars().all()
        if not active_cas:
            await self.create_new_ca("Auto CA")
            return
        if len(active_cas) > 1:
            return
        ca = active_cas[0]
        if ca.not_after - now <= timedelta(days=182):
            await self.create_new_ca(f"Rotated CA {now.date()}")

    async def issue_or_rotate_client_cert(
        self, client: Client, public_key_str: str, client_ip: str, cidr_prefix: int | None = None
    ) -> Tuple[str, datetime, datetime]:
        """Issue or reuse a Nebula host certificate for client using provided public key.

        Args:
            client: The client to issue cert for
            public_key_str: The client's public key
            client_ip: The client's IP address (without CIDR)
            cidr_prefix: Network prefix length (e.g., 16 for /16). If None, uses /32.
        """
        from sqlalchemy import desc

        # Compute current issuance context
        ip_with_cidr = f"{client_ip}/{cidr_prefix}" if cidr_prefix else f"{client_ip}/32"
        # Hash groups for change detection
        import hashlib
        group_names = []
        try:
            if hasattr(client, "groups") and client.groups:
                group_names = sorted([g.name for g in client.groups])
        except Exception:
            # Groups may not be loaded; defaults to empty list
            group_names = []
        groups_hash = hashlib.sha256(",".join(group_names).encode()).hexdigest() if group_names else ""

        existing = (
            await self.session.execute(
                select(ClientCertificate)
                .where(ClientCertificate.client_id == client.id)
                .order_by(desc(ClientCertificate.created_at))
            )
        ).scalars().first()
        now = datetime.utcnow()
        # Reuse existing cert if:
        # - It exists and is not revoked
        # - Not close to expiry (>= 7 days remaining)
        # - Issuance context unchanged (IP/CIDR and groups hash)
        if existing and not existing.revoked and (existing.not_after - now).days >= 7:
            if (
                existing.issued_for_ip_cidr == ip_with_cidr
                and (existing.issued_for_groups_hash or "") == (groups_hash or "")
            ):
                return existing.pem_cert, existing.not_before, existing.not_after

        active_cas = (
            await self.session.execute(
                select(CACertificate).where(CACertificate.is_active == True, CACertificate.can_sign == True)
            )
        ).scalars().all()
        if not active_cas:
            raise RuntimeError("No active CA")
        ca = sorted(active_cas, key=lambda c: c.not_after, reverse=True)[0]

        # Use nebula-cert sign with -in-pub
        with tempfile.TemporaryDirectory() as td:
            pub_path = os.path.join(td, "host.pub")
            ca_crt = os.path.join(td, "ca.crt")
            ca_key = os.path.join(td, "ca.key")
            out_crt = os.path.join(td, "host.crt")
            with open(pub_path, "w") as f:
                f.write(public_key_str.strip() + "\n")
            with open(ca_crt, "wb") as f:
                f.write(ca.pem_cert)
            with open(ca_key, "wb") as f:
                f.write(ca.pem_key)

            # Convert days -> hours for nebula-cert duration
            duration_hours = settings.client_cert_validity_days * 24
            duration = f"{duration_hours}h"
            
            # Build groups argument: concatenate all group names from client.groups (many-to-many)
            groups_arg: list[str] = []
            if group_names:
                groups_arg = ["-groups", ",".join(group_names)]

            cmd = [
                "nebula-cert",
                "sign",
                "-name",
                client.name,
                "-ip",
                ip_with_cidr,
                "-duration",
                duration,
                "-ca-crt",
                ca_crt,
                "-ca-key",
                ca_key,
                "-in-pub",
                pub_path,
                "-out-crt",
                out_crt,
            ] + groups_arg

            try:
                subprocess.check_output(cmd, cwd=td, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                error_msg = e.output.decode(errors="replace")
                print(f"[nebula-cert sign error] {error_msg}")
                raise RuntimeError(f"nebula-cert sign failed: {error_msg}")

            with open(out_crt, "r") as f:
                pem_cert = f.read()

            # Extract fingerprint via nebula-cert print -json
            try:
                out = subprocess.check_output([
                    "nebula-cert", "print", "-json", "-path", out_crt
                ], cwd=td)
                import json as _json
                info = _json.loads(out.decode())
                fingerprint = info.get("fingerprint") or info.get("Fingerprint")
            except Exception:
                # nebula-cert print may fail; fingerprint is optional
                fingerprint = None

        not_after = now + timedelta(days=settings.client_cert_validity_days)
        cc = ClientCertificate(
            client_id=client.id,
            pem_cert=pem_cert,
            not_before=now,
            not_after=not_after,
            fingerprint=fingerprint,
            issued_for_ip_cidr=ip_with_cidr,
            issued_for_groups_hash=groups_hash,
        )
        self.session.add(cc)
        await self.session.commit()
        return pem_cert, now, not_after

    async def import_existing_ca(self, name: str, pem_cert: str, pem_key: str) -> CACertificate:
        now = datetime.utcnow()
        ca = CACertificate(
            name=name,
            pem_cert=pem_cert.encode(),
            pem_key=pem_key.encode(),
            not_before=now,
            not_after=now + timedelta(days=settings.ca_default_validity_days),
            is_active=True,
            is_previous=False,
            can_sign=True,
            include_in_config=True,
        )
        self.session.add(ca)
        await self.session.commit()
        return ca

    async def import_public_ca(self, name: str, pem_cert: str) -> CACertificate:
        """Import a CA certificate without its private key for inclusion in client configs only.
        Extract validity dates using nebula-cert print -json when possible.
        """
        now = datetime.utcnow()
        nb = now
        na = now + timedelta(days=settings.ca_default_validity_days)
        # Try to parse validity from nebula-cert print -json
        try:
            import json as _json, tempfile as _tf, os as _os, subprocess as _sp
            with _tf.TemporaryDirectory() as td:
                p = _os.path.join(td, "ca.crt")
                with open(p, "w") as f:
                    f.write(pem_cert.strip() + "\n")
                out = _sp.check_output(["nebula-cert", "print", "-json", "-path", p])
                info = _json.loads(out.decode())
                # notBefore/notAfter may be strings
                nb_s = info.get("notBefore") or info.get("NotBefore")
                na_s = info.get("notAfter") or info.get("NotAfter")
                from datetime import datetime as _dt
                for v, attr in [(nb_s, "nb"), (na_s, "na")]:
                    if isinstance(v, str):
                        try:
                            # Nebula uses RFC3339 style
                            dt = _dt.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
                            if attr == "nb":
                                nb = dt
                            else:
                                na = dt
                        except Exception:
                            pass
        except Exception:
            pass
        ca = CACertificate(
            name=name,
            pem_cert=pem_cert.encode(),
            pem_key=b"",
            not_before=nb,
            not_after=na,
            is_active=False,
            is_previous=True,
            can_sign=False,
            include_in_config=True,
        )
        self.session.add(ca)
        await self.session.commit()
        return ca
