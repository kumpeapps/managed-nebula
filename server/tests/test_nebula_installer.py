"""Tests for Nebula installer version detection."""

from app.services import nebula_installer
from app.services.nebula_installer import NebulaInstaller


class DummyCompletedProcess:
    def __init__(self, stdout: str):
        self.stdout = stdout


def test_get_installed_version_parses_colon_format(tmp_path, monkeypatch):
    binary_path = tmp_path / "nebula"
    binary_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(nebula_installer, "NEBULA_BIN_PATH", binary_path)
    monkeypatch.setattr(
        nebula_installer.subprocess,
        "run",
        lambda *args, **kwargs: DummyCompletedProcess(stdout="Version: 1.10.3\n"),
    )

    installer = NebulaInstaller()
    assert installer.get_installed_version() == "1.10.3"


def test_get_installed_version_parses_nebula_version_format(tmp_path, monkeypatch):
    binary_path = tmp_path / "nebula"
    binary_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(nebula_installer, "NEBULA_BIN_PATH", binary_path)
    monkeypatch.setattr(
        nebula_installer.subprocess,
        "run",
        lambda *args, **kwargs: DummyCompletedProcess(stdout="Nebula version v1.10.3\n"),
    )

    installer = NebulaInstaller()
    assert installer.get_installed_version() == "1.10.3"


def test_get_installed_version_returns_none_for_unparseable_output(tmp_path, monkeypatch):
    binary_path = tmp_path / "nebula"
    binary_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(nebula_installer, "NEBULA_BIN_PATH", binary_path)
    monkeypatch.setattr(
        nebula_installer.subprocess,
        "run",
        lambda *args, **kwargs: DummyCompletedProcess(stdout="Nebula build metadata only\n"),
    )

    installer = NebulaInstaller()
    assert installer.get_installed_version() is None
