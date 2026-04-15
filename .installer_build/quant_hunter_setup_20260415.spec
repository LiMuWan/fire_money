# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\tools\\install_bundle_stub.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\18335\\Documents\\New project\\releases\\quant_hunter_portable_20260415_120215.zip', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='quant_hunter_setup_20260415',
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
)
