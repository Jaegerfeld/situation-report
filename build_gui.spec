# =============================================================================
# PyInstaller spec for SituationReport GUI
# Builds a self-contained one-folder app (no Python install required).
#
# Windows : dist/SituationReport/SituationReport.exe
# macOS   : dist/SituationReport.app
#
# Usage:
#   pip install pyinstaller
#   pyinstaller build_gui.spec
# =============================================================================

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

# --- Package data collection -------------------------------------------------

# plotly needs its template/schema JSON files
plotly_datas = collect_data_files("plotly")

# openpyxl needs its XML templates
openpyxl_datas = collect_data_files("openpyxl")

# kaleido 1.x: Python files + any data
kaleido_datas, kaleido_binaries, kaleido_hiddenimports = collect_all("kaleido")

# choreographer ships the bundled Chrome binary under cli/browser_exe/
# collect_all captures both the Python sources and the native binaries
choreo_datas, choreo_binaries, choreo_hiddenimports = collect_all("choreographer")

all_datas = plotly_datas + openpyxl_datas + kaleido_datas + choreo_datas
all_binaries = kaleido_binaries + choreo_binaries
all_hiddenimports = (
    [
        # build_reports package and all metric plugins
        "build_reports",
        "build_reports.gui",
        "build_reports.cli",
        "build_reports.loader",
        "build_reports.filters",
        "build_reports.export",
        "build_reports.terminology",
        "build_reports.metrics",
        "build_reports.metrics.base",
        "build_reports.metrics.flow_time",
        "build_reports.metrics.flow_velocity",
        "build_reports.metrics.flow_load",
        "build_reports.metrics.cfd",
        "build_reports.metrics.flow_distribution",
        # core runtime imports
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.scrolledtext",
        "_tkinter",
        "openpyxl",
        "pypdf",
        "kaleido",
        "plotly",
        "plotly.graph_objects",
        "plotly.express",
        "plotly.io",
        "plotly.offline",
    ]
    + kaleido_hiddenimports
    + choreo_hiddenimports
)

# --- Analysis ----------------------------------------------------------------

a = Analysis(
    ["build_reports_gui.pyw"],
    pathex=["."],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # exclude heavy packages that are not used
    excludes=["matplotlib", "numpy", "scipy", "PIL", "IPython", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- Executable --------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SituationReport",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX disabled — can corrupt Chrome DLLs
    console=False,      # no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# --- Collection (one-folder bundle) ------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SituationReport",
)

# --- macOS .app bundle -------------------------------------------------------

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="SituationReport.app",
        icon=None,
        bundle_identifier="com.jaegerfeld.situationreport",
        info_plist={
            "CFBundleName": "SituationReport",
            "CFBundleDisplayName": "SituationReport",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
