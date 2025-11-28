# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NebulaAgentService.exe
Ensures all dependencies are properly bundled for Windows Service
"""

block_cipher = None

a = Analysis(
    ['service.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Win32 service essentials
        'win32timezone',
        'win32serviceutil',
        'win32service',
        'win32event',
        'servicemanager',
        'win32security',
        'ntsecuritycon',
        
        # HTTP client (httpx and all transports)
        'httpx',
        'httpx._transports',
        'httpx._transports.default',
        'httpx._transports.asgi',
        'httpx._transports.wsgi',
        'httpx._models',
        'httpx._client',
        'httpx._config',
        'httpx._exceptions',
        'httpx._types',
        'httpx._utils',
        
        # httpcore (httpx dependency) - v1.x structure
        'httpcore',
        'httpcore._async',
        'httpcore._sync',
        'httpcore._backends',
        'httpcore._backends.sync',
        'httpcore._backends.auto',
        
        # h11 (HTTP/1.1 protocol)
        'h11',
        
        # SSL/TLS support
        'certifi',
        'ssl',
        
        # YAML parsing
        'yaml',
        
        # Standard library that PyInstaller sometimes misses
        'logging',
        'logging.handlers',
        'pathlib',
        'subprocess',
        'threading',
        'socket',
        'hashlib',
        'json',
        'os',
        'sys',
        'time',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NebulaAgentService',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='installer\\nebula.ico',
)
