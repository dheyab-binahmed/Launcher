from __future__ import annotations

import os
import subprocess
import zipfile
from pathlib import Path
from typing import Callable

from .downloader import DownloadManager
from .errors import InstallError
from .manifest import Manifest, MenuRelease
from .platform_utils import app_temp_root, platform_key, safe_child
from .verifier import verify_file

Status = Callable[[str], None]
Progress = Callable[[int, int], None]


class MenuService:
    """Installs each language/version/revision in an isolated temp directory."""
    def __init__(self, downloader: DownloadManager | None = None) -> None:
        self.downloader = downloader or DownloadManager()

    def manifest(self, url: str) -> Manifest:
        if not url:
            raise InstallError("Release configuration is not available yet.")
        return Manifest.from_json(self.downloader.fetch_text(url))

    def install(self, release: MenuRelease, platform: str, progress: Progress | None = None, status: Status | None = None) -> Path:
        if not release.available or not release.version or not release.revision:
            raise InstallError("This menu release is unavailable.")
        root = safe_child(app_temp_root(), "menus", release.language, release.version, f"revision-{release.revision}")
        root.mkdir(parents=True, exist_ok=True)
        total_size = sum(item.size for item in release.artifacts)
        completed = 0
        for artifact in release.artifacts:
            if status: status(f"Downloading {artifact.filename}…")
            def item_progress(done: int, _total: int, offset: int = completed) -> None:
                if progress: progress(offset + done, total_size)
            self.downloader.download(artifact, safe_child(root, artifact.filename), item_progress)
            completed += artifact.size
        for artifact in release.artifacts:
            verify_file(safe_child(root, artifact.filename), artifact.size, artifact.sha256)
        if platform == "macos":
            return self._install_macos_archive(root, release)
        executable = safe_child(root, release.launch_path or "")
        if not executable.is_file():
            raise InstallError("The verified menu archive does not contain its declared launch file.")
        return executable

    def _install_macos_archive(self, root: Path, release: MenuRelease) -> Path:
        archive = safe_child(root, release.artifacts[0].filename)
        extracted = safe_child(root, "app")
        executable = safe_child(extracted, release.launch_path or "")
        if not executable.exists():
            # A failed or interrupted extraction is discarded before retrying.
            # Extract to a sibling directory first, then atomically publish it.
            staging = safe_child(root, "app.staging")
            if staging.exists():
                import shutil
                shutil.rmtree(staging)
            try:
                with zipfile.ZipFile(archive) as bundle:
                    for member in bundle.infolist():
                        target = safe_child(staging, member.filename)
                        if member.is_dir(): target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with bundle.open(member) as src, target.open("wb") as dst: dst.write(src.read())
                staging.replace(extracted)
            except (OSError, zipfile.BadZipFile) as error:
                if staging.exists():
                    import shutil
                    shutil.rmtree(staging)
                raise InstallError("The macOS menu archive could not be installed.") from error
        if not executable.is_file():
            raise InstallError("The macOS archive does not contain its declared launch file.")
        executable.chmod(executable.stat().st_mode | 0o111)
        return executable

    def launch(self, executable: Path, platform: str) -> subprocess.Popen[bytes]:
        if not executable.is_file(): raise InstallError("The installed menu executable is missing.")
        if platform == "windows":
            # Godot resolves the PCK relative to the menu's working directory.
            return subprocess.Popen([str(executable)], cwd=str(executable.parent))
        return subprocess.Popen(["open", "-a", str(executable.parents[2])])

    def prepare_and_launch(self, manifest_url: str, language: str, progress: Progress | None = None, status: Status | None = None) -> tuple[Manifest, Path]:
        manifest = self.manifest(manifest_url)
        platform = platform_key()
        release = manifest.menu_for(language, platform)
        executable = self.install(release, platform, progress, status)
        self.launch(executable, platform)
        return manifest, executable
