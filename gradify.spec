block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("data/bank_notes.xlsx", "data"),
        ("data/guide", "data/guide"),
        ("version.txt", "."),
        ("app.py", "."),
        ("core", "core"),
        ("output", "output"),
        (".streamlit", ".streamlit"),
        ("feedback_config.py", "."),
        ("core/name_detector", "core/name_detector"),
    ],
    hiddenimports=[
        "streamlit", "pandas", "openpyxl",
        "webview", "PIL",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="Gradify",
    debug=False,
    console=False,
    icon="Gradify App Icon Design/exports/gradify-icon.ico",
)
