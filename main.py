import os
import sys
from pathlib import Path

# PySide6 ships Qt DLLs beside its extension modules. Make that directory
# discoverable before importing Qt when running from a PyInstaller onedir app.
if getattr(sys, "frozen", False) and hasattr(os, "add_dll_directory"):
    os.add_dll_directory(str(Path(sys._MEIPASS) / "PySide6"))

from ui.window import run

if __name__ == "__main__":
    bundled_defaults = Path(__file__).resolve().parent / "config" / "settings.json"
    user_config = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Launcher" / "settings.json"
    raise SystemExit(run(user_config, bundled_defaults))
