# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\codd_proj\\cypy\\cypy\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\codd_proj\\cypy\\assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['polars', 'scipy', 'matplotlib', 'lxml', 'tkinter', 'sqlite3', 'IPython', 'notebook'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cypy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['E:\\codd_proj\\cypy\\assets\\favicon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cypy',
)
