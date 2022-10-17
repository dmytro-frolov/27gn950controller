# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[('icon-black.png', './'), ('icon-white.png', './')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='BiasController',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BiasController',
)
app = BUNDLE(
    coll,
    name='BiasController.app',
    icon="icon-black.png",
    bundle_identifier=None,
    info_plist={
     'LSUIElement': True,
     'NSPrincipalClass': 'NSApplication',
    }
)