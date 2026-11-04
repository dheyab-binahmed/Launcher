from __future__ import annotations

import sys
from pathlib import Path

from .downloader import DownloadManager
from .manifest import Artifact
from .platform_utils import app_temp_root, platform_key, safe_child


def is_newer(candidate: str, current: str) -> bool:
    def tokens(value: str) -> tuple[int, ...]:
        import re
        return tuple(int(x) for x in re.findall(r"\d+", value)) or (0,)
    return tokens(candidate) > tokens(current)


class LauncherUpdater:
    """Stages only verified assets. Platform replacement is intentionally delegated to CI/release installer."""
    def __init__(self, downloader: DownloadManager | None = None) -> None:
        self.downloader = downloader or DownloadManager()

    def stage(self, artifact: Artifact) -> Path:
        root = safe_child(app_temp_root(), "launcher-update", platform_key())
        return self.downloader.download(artifact, safe_child(root, artifact.filename))
