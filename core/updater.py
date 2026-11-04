from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path

from .downloader import DownloadManager
from .errors import InstallError
from .manifest import Artifact, Manifest
from .platform_utils import app_temp_root, platform_key, safe_child


def is_newer(candidate: str, current: str) -> bool:
    def tokens(value: str) -> tuple[int, ...]:
        import re
        return tuple(int(x) for x in re.findall(r"\d+", value)) or (0,)
    return tokens(candidate) > tokens(current)


class LauncherUpdater:
    """Safely stage and hand off a verified onedir launcher update.

    Replacement happens in a short-lived helper after this process exits; this
    class never overwrites the executable currently in use.
    """
    def __init__(self, downloader: DownloadManager | None = None) -> None:
        self.downloader = downloader or DownloadManager()

    def stage(self, artifact: Artifact) -> Path:
        root = safe_child(app_temp_root(), "launcher-update", platform_key())
        return self.downloader.download(artifact, safe_child(root, artifact.filename))

    def available(self, manifest: Manifest, current_version: str) -> Artifact | None:
        artifact = manifest.launcher.get(platform_key())
        return artifact if artifact and is_newer(manifest.launcher_version, current_version) else None

    def apply_and_restart(self, archive: Path) -> None:
        if not getattr(sys, "frozen", False):
            raise InstallError("Launcher updates can only be installed from the packaged launcher.")
        if platform_key() == "windows":
            self._apply_windows(archive)
        else:
            self._apply_macos(archive)

    def _apply_windows(self, archive: Path) -> None:
        current = Path(sys.executable).resolve().parent
        staging = Path(tempfile.mkdtemp(prefix="melu-launcher-update-", dir=app_temp_root()))
        try:
            with zipfile.ZipFile(archive) as bundle:
                for item in bundle.infolist():
                    target = safe_child(staging, item.filename)
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with bundle.open(item) as src, target.open("wb") as dst:
                            dst.write(src.read())
        except (OSError, zipfile.BadZipFile) as error:
            raise InstallError("The launcher update archive is invalid.") from error
        candidates = list(staging.rglob("MeluLauncher.exe"))
        if len(candidates) != 1:
            raise InstallError("The launcher update archive has an invalid layout.")
        new_root = candidates[0].parent
        script = staging / "replace-launcher.cmd"
        script.write_text(textwrap.dedent(f"""\
            @echo off
            ping 127.0.0.1 -n 3 > nul
            set \"old={current}\"
            set \"new={new_root}\"
            set \"backup={current}.previous\"
            if exist \"%backup%\" rmdir /s /q \"%backup%\"
            move \"%old%\" \"%backup%\" || exit /b 1
            move \"%new%\" \"%old%\" || (move \"%backup%\" \"%old%\" & exit /b 1)
            start \"\" \"%old%\\MeluLauncher.exe\"
            rmdir /s /q \"%backup%\"
        """), encoding="utf-8")
        subprocess.Popen(["cmd", "/c", str(script)], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def _apply_macos(self, archive: Path) -> None:
        app = Path(sys.executable).resolve().parents[2]
        staging = Path(tempfile.mkdtemp(prefix="melu-launcher-update-", dir=app_temp_root()))
        try:
            with zipfile.ZipFile(archive) as bundle:
                for item in bundle.infolist():
                    target = safe_child(staging, item.filename)
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with bundle.open(item) as src, target.open("wb") as dst:
                            dst.write(src.read())
        except (OSError, zipfile.BadZipFile) as error:
            raise InstallError("The launcher update archive is invalid.") from error
        candidates = list(staging.rglob("MeluLauncher.app"))
        if len(candidates) != 1:
            raise InstallError("The launcher update archive has an invalid layout.")
        new_app = candidates[0]
        script = staging / "replace-launcher.sh"
        script.write_text(textwrap.dedent(f"""\
            #!/bin/sh
            sleep 2
            old={str(app)!r}
            new={str(new_app)!r}
            backup="$old.previous"
            rm -rf "$backup"
            mv "$old" "$backup" && mv "$new" "$old" && open "$old" || mv "$backup" "$old"
        """), encoding="utf-8")
        script.chmod(0o700)
        subprocess.Popen(["/bin/sh", str(script)], start_new_session=True)
