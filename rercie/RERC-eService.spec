# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

asset_root = Path.cwd().parent / "assets"
if not asset_root.is_dir():
    asset_root = Path.cwd().parent / "site-src" / "assets"

a = Analysis(
    ["rercie.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["rercie_core", "rercie_quality"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RERC-eService",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(asset_root / "rerc-e.ico"),
)

collect = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="RERC-eService",
)
