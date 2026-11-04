from __future__ import annotations

import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from .errors import DownloadError
from .manifest import Artifact
from .verifier import verify_file

Progress = Callable[[int, int], None]


class DownloadManager:
    def __init__(self, timeout: int = 20, retries: int = 3) -> None:
        self.timeout, self.retries = timeout, retries

    def fetch_text(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "MeluLauncher/1"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as error:
            raise DownloadError("Could not retrieve update information. Check your internet connection.") from error

    def download(self, artifact: Artifact, destination: Path, progress: Progress | None = None) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            try:
                verify_file(destination, artifact.size, artifact.sha256)
                return destination
            except Exception:
                destination.unlink(missing_ok=True)
        partial = destination.with_suffix(destination.suffix + ".part")
        for attempt in range(self.retries):
            partial.unlink(missing_ok=True)
            written = 0
            try:
                request = urllib.request.Request(artifact.url, headers={"User-Agent": "MeluLauncher/1"})
                with urllib.request.urlopen(request, timeout=self.timeout) as response, partial.open("wb") as out:
                    while chunk := response.read(1024 * 256):
                        out.write(chunk); written += len(chunk)
                        if progress: progress(written, artifact.size)
                verify_file(partial, artifact.size, artifact.sha256)
                partial.replace(destination)
                return destination
            except (OSError, urllib.error.URLError, TimeoutError, Exception) as error:
                partial.unlink(missing_ok=True)
                if attempt == self.retries - 1:
                    if isinstance(error, Exception) and error.__class__.__name__ in {"VerificationError"}:
                        raise error
                    raise DownloadError(f"Download failed for {artifact.filename}: {error}") from error
                time.sleep(1 + attempt)
        raise DownloadError("Download failed")
