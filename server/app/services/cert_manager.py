"""
Nebula Certificate Manager

Handles CA and client certificate lifecycle using nebula-cert CLI.

Certificate Version Support:
- v1: Traditional Nebula certificates (single IPv4 only, all Nebula versions)
- v2: Modern Nebula certificates (IPv4/IPv6, multiple IPs, requires Nebula 1.10.0+)
- hybrid: Dual v1+v2 certificates (backward compatible, single IPv4 only)

Hybrid Certificate Mode:
When hybrid mode is enabled (via GlobalSettings.cert_version = 'hybrid'), client certificates
are issued as BOTH v1 and v2 certificates with the same public key, concatenated in a single
PEM file. This provides backward compatibility with older Nebula clients while supporting
newer v2 clients.

Hybrid Constraints:
- Only single IPv4 address supported (no multiple IPs, no IPv6)
- Requires a v2 CA (v2 CAs can sign both v1 and v2 certificates)
- Both certificate versions use the same public key
- Nebula clients automatically select the appropriate certificate version during handshake

Example hybrid certificate flow:
1. Client sends public key to server
2. Server signs public key TWICE (once with -version 1, once with -version 2)
3. Both PEM certificates are concatenated: v1_pem + v2_pem
4. Client receives combined PEM containing both versions
5. During handshake, Nebula automatically uses the matching version
"""
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

    async def create_new_ca(self, name: str, cert_version: str = "v1") -> CACertificate:
        """Create a new CA certificate.
        
        Args:
            name: CA name
            cert_version: Certificate version - v1, v2, or hybrid
                - v1: Traditional single-signature CA (compatible with all Nebula versions)
                - v2: V2-only CA (requires Nebula 1.10.0+, uses -version 2 flag)
                - hybrid: Dual-signature CA (backward compatible, but client certs are limited to single IPv4)
                
        Note: Hybrid CAs can sign both v1 and v2 client certificates. However, for maximum compatibility,
        hybrid client certificates (containing both v1 and v2 signatures) are restricted to single IPv4 
        addresses only. This ensures the networks match between v1 and v2 certificate versions, as required
        by Nebula's dual-cert implementation.
        """
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
            # Add -version flag for pure v2 CAs only
            # Hybrid mode: CA without -version flag can sign both v1 and v2 certs
            # We then manually issue both versions for client certs
            if cert_version == "v2":
                cmd.extend(["-version", "2"])
            
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
            c.is_active = False
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
            cert_version=cert_version,
            nebula_version="1.10.0",
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
        self, client: Client, public_key_str: str, client_ip: str, cidr_prefix: int | None = None,
        cert_version: str = "v1", all_ips: list[str] | None = None
    ) -> Tuple[str, datetime, datetime]:
        """Issue or reuse a Nebula host certificate for client using provided public key.

        Args:
            client: The client to issue cert for
            public_key_str: The client's public key
            client_ip: The client's IP address (without CIDR) - primary IP for v1
            cidr_prefix: Network prefix length (e.g., 16 for /16). If None, uses /32.
            cert_version: Certificate version (v1, v2, or hybrid)
                - v1: Traditional single IPv4 certificate
                - v2: V2-only certificate (supports multiple IPs, IPv6)
                - hybrid: Dual v1+v2 certificate (single IPv4 only, for backwards compatibility)
            all_ips: List of all IP addresses for v2 certs (optional, v2 only, not supported for hybrid)
        """
        from sqlalchemy import desc

        # Validate constraints for hybrid certificates
        if cert_version == "hybrid":
            if all_ips and len(all_ips) > 1:
                raise ValueError("Hybrid certificates do not support multiple IPs - only single IPv4 address allowed")
            # Validate that the IP is IPv4
            import ipaddress
            try:
                ip_obj = ipaddress.ip_address(client_ip)
                if ip_obj.version != 4:
                    raise ValueError("Hybrid certificates only support IPv4 addresses")
            except ValueError as e:
                raise ValueError(f"Invalid IP address for hybrid certificate: {e}")

        # Compute current issuance context
        ip_with_cidr = f"{client_ip}/{cidr_prefix}" if cidr_prefix else f"{client_ip}/32"
        
        # For v2 certs with multiple IPs, create a sorted comma-separated list for comparison
        # Note: hybrid certs use single IP only
        all_ips_str = None
        if cert_version == "v2" and all_ips:
            all_ips_str = ",".join(sorted(all_ips))
        
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

        # Get the current active CA before checking existing cert
        active_cas = (
            await self.session.execute(
                select(CACertificate).where(CACertificate.is_active == True, CACertificate.can_sign == True)
            )
        ).scalars().all()
        if not active_cas:
            raise RuntimeError("No active CA")
        
        # CRITICAL: Always prefer v2 CAs for signing all certificates
        # V2 CAs are backwards compatible and can sign both v1 and v2 format certificates
        # This ensures all clients get certificates from the same CA family
        # Note: v2 CERTIFICATES (not CAs) require Nebula 1.10.0+, but v2 CAs work with all versions
        v2_cas = [ca for ca in active_cas if ca.cert_version == "v2"]
        if v2_cas:
            ca = sorted(v2_cas, key=lambda c: c.not_after, reverse=True)[0]
        else:
            # Fall back to v1 CA if no v2 CA exists
            ca = sorted(active_cas, key=lambda c: c.not_after, reverse=True)[0]
        
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
        # - Certificate version matches what we need
        # - Issuance context unchanged (IP/CIDR, all IPs for v2, and groups hash)
        # - Signed by the same CA (issued_by_ca_id matches current CA)
        if existing and not existing.revoked and (existing.not_after - now).days >= 7:
            # Check if CA has changed - must reissue if different CA
            existing_ca_id = getattr(existing, 'issued_by_ca_id', None)
            # If issued_by_ca_id is None (old cert before this field existed) or doesn't match current CA
            if existing_ca_id is None or existing_ca_id != ca.id:
                # CA has changed (or unknown) - must issue new certificate
                # Update client's config_last_changed_at to signal config refresh needed
                client.config_last_changed_at = datetime.utcnow()
                await self.session.commit()
                pass  # Fall through to issue new cert
            else:
                # Check cert version compatibility
                existing_cert_version = getattr(existing, 'cert_version', 'v1')
                
                # CRITICAL: Validate that the actual PEM content matches the cert_version field
                # This catches cases where cert_version='v1' but PEM contains v2 data (bug in older code)
                pem_content = existing.pem_cert or ""
                actual_is_v2 = "NEBULA CERTIFICATE V2" in pem_content
                actual_is_hybrid = pem_content.count("-----BEGIN NEBULA") >= 2
                
                pem_format_mismatch = False
                # If PEM format doesn't match database field, must regenerate
                if actual_is_hybrid and existing_cert_version != 'hybrid':
                    # Database says not hybrid but PEM has multiple certs
                    pem_format_mismatch = True
                elif actual_is_v2 and not actual_is_hybrid and existing_cert_version != 'v2':
                    # Database says not v2 but PEM is v2 format
                    pem_format_mismatch = True
                elif not actual_is_v2 and not actual_is_hybrid and existing_cert_version != 'v1':
                    # Database says not v1 but PEM is v1 format
                    pem_format_mismatch = True
                
                if not pem_format_mismatch:
                    # PEM format matches database field - continue with normal reuse checks
                    
                    # For v2 certs with multiple IPs, check if all_ips match
                    # For hybrid certs, check single IP only
                    ips_match = True
                    if cert_version == "v2" and all_ips:
                        # Must have matching cert version for v2
                        if existing_cert_version != 'v2':
                            # Existing cert is not v2 - must regenerate
                            ips_match = False
                        else:
                            # Compare all IPs for v2 certificates
                            existing_all_ips = getattr(existing, 'issued_for_all_ips', None)
                            ips_match = (existing_all_ips == all_ips_str)
                    elif cert_version == "hybrid":
                        # Hybrid certs must match version and single IP
                        if existing_cert_version != 'hybrid':
                            ips_match = False
                        else:
                            ips_match = (existing.issued_for_ip_cidr == ip_with_cidr)
                    else:
                        # For v1 certs, only check primary IP and version
                        if existing_cert_version != 'v1':
                            # Existing is not v1 - must regenerate
                            ips_match = False
                        else:
                            ips_match = (existing.issued_for_ip_cidr == ip_with_cidr)
                    
                    if (
                        ips_match
                        and (existing.issued_for_groups_hash or "") == (groups_hash or "")
                    ):
                        return existing.pem_cert, existing.not_before, existing.not_after
        
        # Validate that hybrid mode requires a v2 CA (v2 CAs can sign both v1 and v2)
        if cert_version == "hybrid" and ca.cert_version != "v2":
            raise ValueError(
                f"Hybrid certificate mode requires a v2 CA (v2 CAs can sign both v1 and v2 certificates). "
                f"Current CA '{ca.name}' is version '{ca.cert_version}'. "
                f"Please create a new v2 CA before using hybrid mode."
            )

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

            # For hybrid certificates, we need to issue both v1 and v2 certs with the same public key
            # and concatenate the PEM outputs
            if cert_version == "hybrid":
                # Issue v1 certificate
                # CRITICAL: Must specify -version 1 explicitly (nebula-cert defaults to v2)
                out_crt_v1 = os.path.join(td, "host_v1.crt")
                cmd_v1 = [
                    "nebula-cert",
                    "sign",
                    "-name",
                    client.name,
                    "-duration",
                    duration,
                    "-ca-crt",
                    ca_crt,
                    "-ca-key",
                    ca_key,
                    "-in-pub",
                    pub_path,
                    "-out-crt",
                    out_crt_v1,
                    "-ip",
                    ip_with_cidr,
                    "-version",
                    "1",
                ] + groups_arg
                
                try:
                    subprocess.check_output(cmd_v1, cwd=td, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    error_msg = e.output.decode(errors="replace")
                    print(f"[nebula-cert sign v1 error] {error_msg}")
                    raise RuntimeError(f"nebula-cert sign v1 failed: {error_msg}")
                
                # Issue v2 certificate with same public key and IP
                out_crt_v2 = os.path.join(td, "host_v2.crt")
                cmd_v2 = [
                    "nebula-cert",
                    "sign",
                    "-name",
                    client.name,
                    "-duration",
                    duration,
                    "-ca-crt",
                    ca_crt,
                    "-ca-key",
                    ca_key,
                    "-in-pub",
                    pub_path,
                    "-out-crt",
                    out_crt_v2,
                    "-networks",
                    ip_with_cidr,
                    "-version",
                    "2",
                ] + groups_arg
                
                try:
                    subprocess.check_output(cmd_v2, cwd=td, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    error_msg = e.output.decode(errors="replace")
                    print(f"[nebula-cert sign v2 error] {error_msg}")
                    raise RuntimeError(f"nebula-cert sign v2 failed: {error_msg}")
            else:
                # Standard v1 or v2 certificate issuance
                cmd = [
                    "nebula-cert",
                    "sign",
                    "-name",
                    client.name,
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
                ]
                
                # Add IP addresses and version flag
                if cert_version == "v2" and all_ips:
                    # v2: Multiple IPs using -networks with comma-separated list
                    networks_list = [f"{ip}/{cidr_prefix}" if cidr_prefix else f"{ip}/32" for ip in all_ips]
                    networks_str = ",".join(networks_list)
                    cmd.extend(["-networks", networks_str])
                    cmd.extend(["-version", "2"])
                else:
                    # v1: Single IP only with -ip flag
                    # CRITICAL: Must explicitly specify -version 1 (newer nebula-cert defaults to v2)
                    cmd.extend(["-ip", ip_with_cidr])
                    cmd.extend(["-version", "1"])
                
                cmd.extend(groups_arg)

                try:
                    subprocess.check_output(cmd, cwd=td, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    error_msg = e.output.decode(errors="replace")
                    print(f"[nebula-cert sign error] {error_msg}")
                    raise RuntimeError(f"nebula-cert sign failed: {error_msg}")

            # Read certificate(s) and concatenate for hybrid
            if cert_version == "hybrid":
                # Concatenate v1 and v2 PEMs
                with open(out_crt_v1, "r") as f:
                    pem_cert_v1 = f.read()
                with open(out_crt_v2, "r") as f:
                    pem_cert_v2 = f.read()
                # Combine both certificates in the same PEM file
                pem_cert = pem_cert_v1 + pem_cert_v2
                
                # Extract fingerprint from v2 cert (use v2 as primary for hybrid)
                try:
                    out = subprocess.check_output([
                        "nebula-cert", "print", "-json", "-path", out_crt_v2
                    ], cwd=td)
                    import json as _json
                    info = _json.loads(out.decode())
                    fingerprint = info.get("fingerprint") or info.get("Fingerprint")
                except Exception:
                    fingerprint = None
            else:
                # Standard single certificate
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
            issued_for_all_ips=all_ips_str,  # Store all IPs for v2 cert change detection
            cert_version=cert_version,
            issued_by_ca_id=ca.id,  # Track which CA issued this cert for re-issuance detection
        )
        self.session.add(cc)
        await self.session.commit()
        return pem_cert, now, not_after

    async def import_existing_ca(self, name: str, pem_cert: str, pem_key: str) -> CACertificate:
        """Import a CA certificate with its private key, extracting real validity dates from the PEM."""
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
                print(f"[import_existing_ca] nebula-cert output: {info}")
                # notBefore/notAfter may be in details object or at top level
                details = info.get("details", {})
                nb_s = details.get("notBefore") or details.get("NotBefore") or info.get("notBefore") or info.get("NotBefore")
                na_s = details.get("notAfter") or details.get("NotAfter") or info.get("notAfter") or info.get("NotAfter")
                print(f"[import_existing_ca] Extracted dates: nb_s={nb_s}, na_s={na_s}")
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
                        except Exception as e:
                            print(f"[import_existing_ca] Failed to parse {attr}: {e}")
                print(f"[import_existing_ca] Final dates: nb={nb}, na={na}")
        except Exception as e:
            print(f"[import_existing_ca] Failed to extract dates: {e}")
        
        # Mark existing active signing CAs as previous
        active_cas = (
            await self.session.execute(
                select(CACertificate).where(CACertificate.is_active == True, CACertificate.can_sign == True)
            )
        ).scalars().all()
        for c in active_cas:
            c.is_active = False
            c.is_previous = True
            c.include_in_config = True
            await self.session.flush()
        
        ca = CACertificate(
            name=name,
            pem_cert=pem_cert.encode(),
            pem_key=pem_key.encode(),
            not_before=nb,
            not_after=na,
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
                # notBefore/notAfter may be in details object or at top level
                details = info.get("details", {})
                nb_s = details.get("notBefore") or details.get("NotBefore") or info.get("notBefore") or info.get("NotBefore")
                na_s = details.get("notAfter") or details.get("NotAfter") or info.get("notAfter") or info.get("NotAfter")
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
