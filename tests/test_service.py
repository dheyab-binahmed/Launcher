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
