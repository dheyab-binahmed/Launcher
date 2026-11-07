from __future__ import annotations

import socket
import time
import errno
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

from .errors import DownloadError, ManifestUnavailableError, VerificationError
from .manifest import Artifact
from .verifier import verify_file

Progress = Callable[[int, int], None]
MAX_MANIFEST_BYTES = 1024 * 1024


class HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        if urllib.parse.urlparse(new_url).scheme != "https":
            raise urllib.error.URLError("Redirected to a non-HTTPS URL")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


class DownloadManager:
    def __init__(self, timeout: int = 20, retries: int = 3) -> None:
        self.timeout, self.retries = timeout, retries
        self._opener = urllib.request.build_opener(HTTPSRedirectHandler())

    def _open(self, request: urllib.request.Request):
        response = self._opener.open(request, timeout=self.timeout)
        final_url = response.geturl()
        if urllib.parse.urlparse(final_url).scheme != "https":
            response.close()
            raise urllib.error.URLError("Response came from a non-HTTPS URL")
        return response

    def fetch_text(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "MeluLauncher/1"})
        try:
            with self._open(request) as response:
                raw = response.read(MAX_MANIFEST_BYTES + 1)
                if len(raw) > MAX_MANIFEST_BYTES:
                    raise ManifestUnavailableError("The release manifest is too large.")
                return raw.decode("utf-8")
        except urllib.error.HTTPError as error:
            raise ManifestUnavailableError(f"The release manifest is unavailable (HTTP {error.code}).") from error
        except (urllib.error.URLError, socket.timeout, TimeoutError, UnicodeDecodeError) as error:
            raise ManifestUnavailableError("Could not reach the release manifest. Check your internet connection and try again.") from error

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
                with self._open(request) as response, partial.open("xb") as out:
                    while chunk := response.read(1024 * 256):
                        written += len(chunk)
                        if written > artifact.size:
                            raise VerificationError(f"File size check failed for {artifact.filename} (download is too large).")
                        out.write(chunk)
                        if progress: progress(written, artifact.size)
                verify_file(partial, artifact.size, artifact.sha256)
                partial.replace(destination)
                return destination
            except VerificationError:
                partial.unlink(missing_ok=True)
                raise
            except Exception as error:
                partial.unlink(missing_ok=True)
                if attempt == self.retries - 1:
                    if isinstance(error, OSError) and error.errno == errno.ENOSPC:
                        raise DownloadError(f"Not enough disk space to download {artifact.filename}.") from error
                    if isinstance(error, (socket.timeout, TimeoutError)):
                        raise DownloadError(f"Download timed out for {artifact.filename}.") from error
                    if isinstance(error, urllib.error.HTTPError):
                        raise DownloadError(f"Download failed for {artifact.filename} (HTTP {error.code}).") from error
                    raise DownloadError(f"Download failed for {artifact.filename}: {error}") from error
                time.sleep(1 + attempt)
        raise DownloadError("Download failed")
