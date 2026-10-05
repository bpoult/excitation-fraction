# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Sample & Laser Calculations desktop app.
#
#   pyinstaller ExcitationFraction.spec --noconfirm --clean
#
# Output: dist/ExcitationFraction/ExcitationFraction.exe (+ _internal/).
# See build.bat for the full build + zip step.

import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(SPECPATH)

datas, binaries, hiddenimports = [], [], []

# Packages that ship JS/CSS/metadata Dash reads at runtime (component bundles,
# plotly.min.js, dist-info for importlib.metadata) or, for webview, the
# WebView2/.NET DLLs and lazily-imported platform backends.
for pkg in ("dash", "dash_bootstrap_components", "plotly", "webview"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

datas += [
    (os.path.join(ROOT, "configs", "default.json"), "configs"),
    (os.path.join(ROOT, "src", "assets"), os.path.join("src", "assets")),
]

hiddenimports += [
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr",
    "clr_loader",
    "clr_loader.netfx",
    "src",
    "src.app",
    "src.calculations",
    "src.config_io",
    "src.models",
    "src.plots",
]

excludes = [
    # GUI toolkits / plotting libraries the app does not use
    "tkinter", "_tkinter", "matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
    # notebook / test / heavy science stacks
    "IPython", "ipykernel", "jupyter", "jupyter_client", "notebook", "nbformat",
    "pytest", "_pytest", "scipy", "pandas", "sympy", "PIL", "kaleido",
    # optional Dash backends
    "fastapi", "quart", "hypercorn", "uvicorn", "starlette",
    # Dash's Jupyter integration deps (imported inside try/except ImportError)
    "comm", "nest_asyncio", "retrying", "requests",
    "src.tests",
]

a = Analysis(
    [os.path.join(ROOT, "launcher.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# Jupyter extensions, sample datasets, the debug-only renderer and source maps
# are never served by a desktop app running with debug=False.
_DROP_PREFIXES = tuple(
    os.path.join(*parts)
    for parts in (
        ("dash", "labextension"),
        ("dash", "nbextension"),
        ("plotly", "labextension"),
        ("plotly", "package_data", "datasets"),
        ("plotly", "package_data", "widgetbundle.js"),
    )
)
_DROP_SUFFIXES = (".dev.js", ".js.map")


def _keep(dest_name: str) -> bool:
    return not (
        dest_name.startswith(_DROP_PREFIXES) or dest_name.endswith(_DROP_SUFFIXES)
    )


a.datas = [entry for entry in a.datas if _keep(entry[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ExcitationFraction",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=os.path.join(ROOT, "build_assets", "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # UPX corrupts some .NET / WebView2 DLLs
    upx_exclude=[],
    name="ExcitationFraction",
)
