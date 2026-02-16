"""
Nebula Binary Installer Service

Downloads and installs Nebula binaries (nebula and nebula-cert) from GitHub releases.
Supports automatic version management based on GlobalSettings.nebula_version.
"""
import logging
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Installation paths
NEBULA_BIN_PATH = Path("/usr/local/bin/nebula")
NEBULA_CERT_BIN_PATH = Path("/usr/local/bin/nebula-cert")


class NebulaInstaller:
    """Service for installing and managing Nebula binaries on the server."""
    
    def __init__(self):
        """Initialize the Nebula installer service."""
        self.github_repo = "slackhq/nebula"
        self.base_url = "https://github.com"
    
    def get_installed_version(self) -> Optional[str]:
        """
        Get the currently installed Nebula version.
        
        Returns:
            Version string (e.g., "1.10.0") or None if not installed
        """
        if not NEBULA_BIN_PATH.exists():
            logger.info("Nebula binary not found at %s (may be first install)", NEBULA_BIN_PATH)
            return None
        
        try:
            # Security Note: NEBULA_BIN_PATH is a controlled constant (/usr/local/bin/nebula),
            # not user input. This is safe from command injection.
            result = subprocess.run(
                [str(NEBULA_BIN_PATH), "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            
            # Parse version from output like "Nebula version 1.9.7"
            for line in result.stdout.splitlines():
                if "version" in line.lower():
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.lower() == "version" and i + 1 < len(parts):
                            version = parts[i + 1].lstrip('v')
                            logger.info("Detected installed Nebula version: %s", version)
                            return version
            
            logger.warning("Could not parse version from nebula -version output")
            return None
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout running nebula -version")
            return None
        except subprocess.CalledProcessError as e:
            logger.error("Failed to get nebula version: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error getting nebula version: %s", e)
            return None
    
    def _detect_architecture(self) -> Optional[str]:
        """
        Detect the system architecture for downloading the correct binary.
        
        Returns:
            Architecture string for Nebula downloads (e.g., "amd64", "arm64", "arm")
            or None if unsupported
        """
        machine = platform.machine().lower()
        
        arch_map = {
            'x86_64': 'amd64',
            'amd64': 'amd64',
            'aarch64': 'arm64',
            'arm64': 'arm64',
            'armv7l': 'arm',
            'armhf': 'arm',
        }
        
        nebula_arch = arch_map.get(machine)
        if not nebula_arch:
            logger.error("Unsupported architecture: %s", machine)
            return None
        
        logger.info("Detected architecture: %s (Nebula: %s)", machine, nebula_arch)
        return nebula_arch
    
    async def download_and_install(self, version: str, force: bool = False) -> Tuple[bool, str]:
        """
        Download and install a specific Nebula version.
        
        Args:
            version: Version string (e.g., "1.10.0") without 'v' prefix
            force: Force installation even if version is already installed
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Normalize version (remove 'v' prefix if present)
        version = version.lstrip('v')
        
        # Check if already installed
        if not force:
            installed_version = self.get_installed_version()
            if installed_version == version:
                msg = f"Nebula {version} is already installed"
                logger.info(msg)
                return True, msg
        
        # Detect architecture
        arch = self._detect_architecture()
        if not arch:
            return False, "Unsupported system architecture"
        
        # Construct download URL
        download_url = (
            f"{self.base_url}/{self.github_repo}/releases/download/"
            f"v{version}/nebula-linux-{arch}.tar.gz"
        )
        
        logger.info("Downloading Nebula %s from %s", version, download_url)
        
        try:
            # Download to temporary directory
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                tar_path = tmpdir_path / "nebula.tar.gz"
                
                # Download with timeout
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                    async with client.stream("GET", download_url) as response:
                        if response.status_code == 404:
                            msg = f"Nebula version {version} not found for architecture {arch}"
                            logger.error(msg)
                            return False, msg
                        
                        response.raise_for_status()
                        
                        # Stream download to file
                        with open(tar_path, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=8192):
                                f.write(chunk)
                
                logger.info("Download complete, extracting...")
                
                # Extract tar.gz with path traversal protection
                with tarfile.open(tar_path, 'r:gz') as tar:
                    # Verify all members are safe before extraction
                    for member in tar.getmembers():
                        member_path = (tmpdir_path / member.name).resolve()
                        if not str(member_path).startswith(str(tmpdir_path.resolve())):
                            msg = f"Unsafe path in archive: {member.name}"
                            logger.error(msg)
                            return False, msg
                    # Safe to extract after validation
                    tar.extractall(tmpdir_path)
                
                # Verify binaries exist
                nebula_tmp = tmpdir_path / "nebula"
                nebula_cert_tmp = tmpdir_path / "nebula-cert"
                
                if not nebula_tmp.exists():
                    msg = "nebula binary not found in downloaded archive"
                    logger.error(msg)
                    return False, msg
                
                if not nebula_cert_tmp.exists():
                    msg = "nebula-cert binary not found in downloaded archive"
                    logger.error(msg)
                    return False, msg
                
                # Verify downloaded version
                # Security Note: nebula_tmp is a Path we created in our controlled tmpdir,
                # not derived from user input. This is safe from command injection.
                result = subprocess.run(
                    [str(nebula_tmp), "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True
                )
                
                downloaded_version = None
                for line in result.stdout.splitlines():
                    if "version" in line.lower():
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.lower() == "version" and i + 1 < len(parts):
                                downloaded_version = parts[i + 1].lstrip('v')
                                break
                
                if downloaded_version != version:
                    msg = f"Version mismatch: expected {version}, got {downloaded_version}"
                    logger.error(msg)
                    return False, msg
                
                logger.info("Verified downloaded Nebula version: %s", downloaded_version)
                
                # Backup existing binaries if they exist
                if NEBULA_BIN_PATH.exists():
                    backup_path = NEBULA_BIN_PATH.parent / f"nebula.backup.{int(os.path.getmtime(NEBULA_BIN_PATH))}"
                    shutil.copy2(NEBULA_BIN_PATH, backup_path)
                    logger.info("Backed up old nebula to %s", backup_path)
                
                if NEBULA_CERT_BIN_PATH.exists():
                    backup_path = NEBULA_CERT_BIN_PATH.parent / f"nebula-cert.backup.{int(os.path.getmtime(NEBULA_CERT_BIN_PATH))}"
                    shutil.copy2(NEBULA_CERT_BIN_PATH, backup_path)
                    logger.info("Backed up old nebula-cert to %s", backup_path)
                
                # Install new binaries
                shutil.copy2(nebula_tmp, NEBULA_BIN_PATH)
                shutil.copy2(nebula_cert_tmp, NEBULA_CERT_BIN_PATH)
                
                # Set executable permissions
                NEBULA_BIN_PATH.chmod(0o755)
                NEBULA_CERT_BIN_PATH.chmod(0o755)
                
                logger.info("Successfully installed Nebula %s", version)
                
                # Verify final installation
                final_version = self.get_installed_version()
                if final_version != version:
                    msg = f"Installation verification failed: expected {version}, got {final_version}"
                    logger.error(msg)
                    return False, msg
                
                msg = f"Successfully installed Nebula {version}"
                return True, msg
                
        except httpx.HTTPError as e:
            msg = f"Download failed: {str(e)}"
            logger.error(msg)
            return False, msg
        except tarfile.TarError as e:
            msg = f"Failed to extract archive: {str(e)}"
            logger.error(msg)
            return False, msg
        except subprocess.CalledProcessError as e:
            msg = f"Failed to verify binary: {str(e)}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Unexpected error during installation: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    async def ensure_version_installed(self, desired_version: str) -> Tuple[bool, str]:
        """
        Ensure the desired Nebula version is installed, installing if necessary.
        
        Args:
            desired_version: Desired version string (e.g., "1.10.0")
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        desired_version = desired_version.lstrip('v')
        installed_version = self.get_installed_version()
        
        if installed_version is None:
            logger.info("Nebula not installed, installing version %s", desired_version)
            return await self.download_and_install(desired_version)
        
        if installed_version == desired_version:
            msg = f"Nebula {desired_version} is already installed"
            logger.info(msg)
            return True, msg
        
        logger.info(
            "Nebula version mismatch: installed=%s, desired=%s. Upgrading...",
            installed_version,
            desired_version
        )
        return await self.download_and_install(desired_version, force=True)
