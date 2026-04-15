# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path.cwd()
version_file = project_root / 'tools' / 'file_version_info.txt'

a = Analysis(
    ['app_qt.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'sample_data'), 'sample_data'),
        (str(project_root / 'quant_hunter' / 'sdk_bridge.py'), 'quant_hunter'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quant_hunter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    version=str(version_file),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='quant_hunter',
)
