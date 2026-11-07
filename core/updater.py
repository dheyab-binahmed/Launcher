from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from .downloader import DownloadManager
from .archive import extract_zip_safely
from .errors import ArchiveError, InstallError
from .manifest import Artifact, Manifest
from .platform_utils import app_temp_root, platform_key, safe_child


def is_newer(candidate: str, current: str) -> bool:
    def tokens(value: str) -> tuple[int, ...]:
        import re
        return tuple(int(x) for x in re.findall(r"\d+", value)) or (0,)
    return tokens(candidate) > tokens(current)


def _powershell_string(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


class LauncherUpdater:
    """Install a verified launcher ZIP only after the running app has exited.

    The downloader validates size and SHA-256 before this class receives an
    archive. The platform helper then waits for this PID, moves the old app to
    a sibling ``.previous`` backup, moves the complete new app into place, and
    starts it. A move/start failure restores that backup.
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

    def _extract_windows_archive(self, archive: Path, staging: Path) -> Path:
        """Safely unpack the exact onedir ZIP emitted by build_windows.ps1."""
        try:
            extract_zip_safely(archive, staging)
        except ArchiveError as error:
            raise InstallError("The launcher update archive is invalid.") from error
        candidates = list(staging.rglob("MeluLauncher.exe"))
        if len(candidates) != 1 or not (candidates[0].parent / "_internal").is_dir():
            raise InstallError("The launcher update archive is not a complete MeluLauncher onedir package.")
        return candidates[0].parent

    def _apply_windows(self, archive: Path) -> None:
        current = Path(sys.executable).resolve().parent
        staging = Path(tempfile.mkdtemp(prefix="melu-launcher-update-", dir=app_temp_root()))
        new_root = self._extract_windows_archive(archive, staging)
        script = staging / "replace-launcher.ps1"
        self._write_windows_helper(script, current, new_root, os.getpid())
        subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    @staticmethod
    def _write_windows_helper(script: Path, current: Path, new_root: Path, pid: int) -> None:
        backup = current.with_name(f"{current.name}.previous-{pid}")
        executable = current / "MeluLauncher.exe"
        script.write_text(textwrap.dedent(f"""\
            $ErrorActionPreference = 'Stop'
            $old = {_powershell_string(current)}
            $new = {_powershell_string(new_root)}
            $backup = {_powershell_string(backup)}
            $executable = {_powershell_string(executable)}
            Wait-Process -Id {pid} -ErrorAction SilentlyContinue
            Move-Item -LiteralPath $old -Destination $backup
            try {{
                Move-Item -LiteralPath $new -Destination $old
                # Starting a process only proves CreateProcess succeeded.  Retain
                # the backup until the replacement has remained alive briefly,
                # so a launcher which exits immediately is recovered too.
                $started = Start-Process -FilePath $executable -PassThru -ErrorAction Stop
                Start-Sleep -Milliseconds 750
                if ($started.HasExited) {{ throw 'Replacement launcher exited during startup.' }}
                # Only discard the previous installation after the new process
                # has survived its startup check.
                Remove-Item -LiteralPath $backup -Recurse -Force -ErrorAction Stop
            }} catch {{
                if (Test-Path -LiteralPath $old) {{ Remove-Item -LiteralPath $old -Recurse -Force }}
                Move-Item -LiteralPath $backup -Destination $old
                throw
            }} finally {{
                # The staged launcher has either been moved into place or
                # discarded during rollback.  Only this helper's own staging
                # directory remains, so it can be safely removed.
                Remove-Item -LiteralPath $PSScriptRoot -Recurse -Force -ErrorAction SilentlyContinue
            }}
        """), encoding="utf-8")

    def _apply_macos(self, archive: Path) -> None:
        # Python's zip extraction loses executable modes and app-bundle
        # metadata. The helper therefore uses ditto after this process exits.
        app = Path(sys.executable).resolve().parents[2]
        root = Path(tempfile.mkdtemp(prefix="melu-launcher-update-", dir=app_temp_root()))
        script = root / "replace-launcher.sh"
        self._write_macos_helper(script, app, archive, os.getpid())
        script.chmod(0o700)
        subprocess.Popen(["/bin/sh", str(script)], start_new_session=True)

    @staticmethod
    def _write_macos_helper(script: Path, app: Path, archive: Path, pid: int) -> None:
        parent = app.parent
        backup = app.with_name(f"{app.name}.previous-{pid}")
        extract = parent / f".{app.stem}.extract-{pid}"
        new_app = parent / f".{app.stem}.update-{pid}.app"
        script.write_text(textwrap.dedent(f"""\
            #!/bin/sh
            set -eu
            old={shlex.quote(str(app))}
            archive={shlex.quote(str(archive))}
            backup={shlex.quote(str(backup))}
            extract={shlex.quote(str(extract))}
            new={shlex.quote(str(new_app))}
            while kill -0 {pid} 2>/dev/null; do sleep 1; done
            mkdir "$extract"
            /usr/bin/ditto -x -k "$archive" "$extract"
            candidate="$extract/MeluLauncher.app"
            test -x "$candidate/Contents/MacOS/MeluLauncher"
            mv "$candidate" "$new"
            rmdir "$extract"
            mv "$old" "$backup"
            if mv "$new" "$old" && open "$old"; then
                exit 0
            fi
            rm -rf "$old"
            mv "$backup" "$old"
            exit 1
        """), encoding="utf-8")
