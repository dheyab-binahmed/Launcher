from pathlib import Path
import pytest
from core.errors import InstallError
from core.launcher import MenuService
from core.manifest import MenuRelease


def test_missing_pck_is_not_launchable(tmp_path: Path):
    release = MenuRelease("en", True, "b1", 1, (), "menu.exe")
    with pytest.raises(InstallError): MenuService().install(release, "windows")


def test_chapter_filtering():
    from core.chapter_manager import ChapterManager
    assert len(ChapterManager.available([{"language": "en", "platform": "windows", "available": True}, {"language": "ru", "platform": "windows", "available": True}], "en", "windows")) == 1


def test_old_blank_manifest_setting_does_not_override_bundled_default(tmp_path: Path):
    from core.settings import Settings
    default = tmp_path / "default.json"; default.write_text('{"manifest_url":"https://example.com/manifest.json"}', encoding="utf-8")
    user = tmp_path / "user.json"; user.write_text('{"manifest_url":"", "language":"ru"}', encoding="utf-8")
    settings = Settings(user, default)
    assert settings.data["manifest_url"] == "https://example.com/manifest.json"
    assert settings.language == "ru"
