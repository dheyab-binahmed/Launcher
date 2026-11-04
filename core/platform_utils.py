from __future__ import annotations

import os
import platform
import tempfile
from pathlib import Path


def platform_key() -> str:
    system = platform.system()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    raise RuntimeError(f"Unsupported operating system: {system}")


def app_temp_root() -> Path:
    # tempfile follows %TEMP% on Windows and macOS's selected temporary directory.
    root = Path(tempfile.gettempdir()).resolve() / "MeluLauncher"
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_child(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve()
    if os.path.commonpath([str(root.resolve()), str(candidate)]) != str(root.resolve()):
        raise ValueError("Unsafe path requested")
    return candidate
