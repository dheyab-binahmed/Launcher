import hashlib
import errno
from pathlib import Path
import urllib.error
import urllib.request
import socket
import pytest
from core.downloader import DownloadManager, HTTPSRedirectHandler
from core.errors import DownloadError, ManifestUnavailableError, VerificationError
from core.manifest import Artifact
from core.errors import InstallError
from core.launcher import MenuService
from core.manifest import MenuRelease


def test_missing_pck_is_not_launchable(tmp_path: Path):
    release = MenuRelease("en", True, "b1", 1, (), "menu.exe")
    with pytest.raises(InstallError): MenuService().install(release, "windows")


def test_chapter_filtering():
    from core.chapter_manager import ChapterManager
    assert len(ChapterManager.available([{"language": "en", "platform": "windows", "available": True}, {"language": "ru", "platform": "windows", "available": True}], "en", "windows")) == 1


def test_persisted_manifest_never_overrides_bundled_build_setting(tmp_path: Path):
    from core.settings import Settings
    default = tmp_path / "default.json"; default.write_text('{"manifest_url":"https://example.com/testing-manifest.json"}', encoding="utf-8")
    user = tmp_path / "user.json"; user.write_text('{"manifest_url":"https://example.com/production-manifest.json", "language":"ru"}', encoding="utf-8")
    settings = Settings(user, default)
    assert settings.data["manifest_url"] == "https://example.com/testing-manifest.json"
    assert settings.language == "ru"


def test_manifest_404_is_not_reported_as_a_game_download_failure(monkeypatch):
    def missing(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://example.com/manifest.json", 404, "Not Found", {}, None)
    manager = DownloadManager()
    monkeypatch.setattr(manager, "_open", missing)
    with pytest.raises(ManifestUnavailableError, match=r"manifest is unavailable \(HTTP 404\)"):
        manager.fetch_text("https://example.com/manifest.json")


class FakeResponse:
    def __init__(self, payload: bytes, url: str = "https://example.com/file") -> None:
        self.payload, self.url, self.position = payload, url, 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.payload) - self.position
        chunk = self.payload[self.position:self.position + size]
        self.position += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self.url


def test_download_streams_only_the_verified_size_and_uses_atomic_final_file(tmp_path, monkeypatch):
    payload = b"verified download"
    artifact = Artifact("https://example.com/file", len(payload), hashlib.sha256(payload).hexdigest(), "game.bin")
    manager = DownloadManager(retries=1)
    monkeypatch.setattr(manager, "_open", lambda _request: FakeResponse(payload))
    destination = tmp_path / artifact.filename
    assert manager.download(artifact, destination) == destination
    assert destination.read_bytes() == payload
    assert not destination.with_suffix(".bin.part").exists()


def test_download_rejects_an_oversized_response_before_installing(tmp_path, monkeypatch):
    payload = b"too much data"
    artifact = Artifact("https://example.com/file", 3, hashlib.sha256(b"bad").hexdigest(), "game.bin")
    manager = DownloadManager(retries=1)
    monkeypatch.setattr(manager, "_open", lambda _request: FakeResponse(payload))
    with pytest.raises(VerificationError, match="too large"):
        manager.download(artifact, tmp_path / artifact.filename)
    assert not (tmp_path / artifact.filename).exists()


def test_download_removes_partial_file_after_interruption(tmp_path, monkeypatch):
    class InterruptedResponse(FakeResponse):
        def read(self, size=-1):
            if self.position:
                raise ConnectionResetError("connection lost")
            return super().read(4)

    payload = b"verified download"
    artifact = Artifact("https://example.com/file", len(payload), hashlib.sha256(payload).hexdigest(), "game.bin")
    manager = DownloadManager(retries=1)
    monkeypatch.setattr(manager, "_open", lambda _request: InterruptedResponse(payload))
    with pytest.raises(DownloadError, match="Download failed"):
        manager.download(artifact, tmp_path / artifact.filename)
    assert not (tmp_path / artifact.filename).exists()
    assert not (tmp_path / "game.bin.part").exists()


def test_download_rejects_bad_hash_and_removes_partial_file(tmp_path, monkeypatch):
    payload = b"verified download"
    artifact = Artifact("https://example.com/file", len(payload), "0" * 64, "game.bin")
    manager = DownloadManager(retries=1)
    monkeypatch.setattr(manager, "_open", lambda _request: FakeResponse(payload))
    with pytest.raises(VerificationError, match="SHA-256"):
        manager.download(artifact, tmp_path / artifact.filename)
    assert not (tmp_path / artifact.filename).exists()
    assert not (tmp_path / "game.bin.part").exists()


def test_download_reports_disk_full(tmp_path, monkeypatch):
    artifact = Artifact("https://example.com/file", 1, "a" * 64, "game.bin")
    manager = DownloadManager(retries=1)
    monkeypatch.setattr(manager, "_open", lambda _request: (_ for _ in ()).throw(OSError(errno.ENOSPC, "disk full")))
    with pytest.raises(DownloadError, match="Not enough disk space"):
        manager.download(artifact, tmp_path / artifact.filename)


def test_https_redirect_handler_rejects_a_downgrade():
    request = urllib.request.Request("https://example.com/file")
    with pytest.raises(urllib.error.URLError, match="non-HTTPS"):
        HTTPSRedirectHandler().redirect_request(request, None, 302, "Found", {}, "http://example.com/file")


@pytest.mark.parametrize(("failure", "message"), [
    (socket.timeout(), "timed out"),
    (urllib.error.HTTPError("https://example.com/file", 503, "Service Unavailable", {}, None), "HTTP 503"),
])
def test_download_reports_timeout_and_http_failures(tmp_path, monkeypatch, failure, message):
    artifact = Artifact("https://example.com/file", 1, "a" * 64, "game.bin")
    manager = DownloadManager(retries=1)
    monkeypatch.setattr(manager, "_open", lambda _request: (_ for _ in ()).throw(failure))
    with pytest.raises(DownloadError, match=message):
        manager.download(artifact, tmp_path / artifact.filename)


@pytest.mark.parametrize(("failure", "message_key"), [
    ("The release manifest is unavailable (HTTP 404).", "manifest_unavailable"),
    ("Invalid JSON.", "manifest_invalid"),
    ("The RU menu is not published for this platform yet.", "release_unavailable"),
    ("Download failed for game.exe", "download_error"),
    ("Download timed out for game.exe", "timeout_error"),
    ("Not enough disk space to install game.exe", "disk_error"),
    ("File size check failed for game.exe", "size_error"),
    ("SHA-256 check failed for game.exe", "sha_error"),
    ("The macOS menu archive could not be installed.", "install_error"),
])
def test_player_errors_identify_the_failed_operation(failure, message_key):
    from ui.language import TEXT
    from ui.window import player_error
    assert player_error(failure, TEXT["en"]) == TEXT["en"][message_key]
