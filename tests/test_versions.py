import json
import stat
import zipfile
from pathlib import Path

import pytest

from core.errors import InstallError
from core.manifest import Manifest
from core.updater import LauncherUpdater, is_newer


def test_version_comparison():
    assert is_newer("0.2.0", "0.1.9")
    assert is_newer("b1.0.0-r2", "b1.0.0-r1")
    assert not is_newer("0.1.0", "0.1.0")


def test_updater_ignores_manifest_without_a_published_launcher_asset(monkeypatch):
    data = {"schema_version": 1, "launcher": {"version": "9.0.0", "assets": {}}, "menus": {}}
    monkeypatch.setattr("core.updater.platform_key", lambda: "windows")
    assert LauncherUpdater().available(Manifest.from_json(json.dumps(data)), "0.1.0") is None


def test_windows_updater_accepts_the_actual_onedir_zip_layout(tmp_path: Path):
    archive = tmp_path / "MeluLauncher-windows.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("MeluLauncher/MeluLauncher.exe", b"launcher")
        bundle.writestr("MeluLauncher/_internal/python.dll", b"runtime")
    root = LauncherUpdater()._extract_windows_archive(archive, tmp_path / "staging")
    assert root.name == "MeluLauncher"
    assert (root / "MeluLauncher.exe").is_file()


def test_windows_updater_rejects_incomplete_or_unsafe_archives(tmp_path: Path):
    incomplete = tmp_path / "incomplete.zip"
    with zipfile.ZipFile(incomplete, "w") as bundle:
        bundle.writestr("MeluLauncher/MeluLauncher.exe", b"launcher")
    with pytest.raises(InstallError, match="complete"):
        LauncherUpdater()._extract_windows_archive(incomplete, tmp_path / "incomplete")

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as bundle:
        bundle.writestr("../MeluLauncher.exe", b"bad")
    with pytest.raises(InstallError, match="invalid"):
        LauncherUpdater()._extract_windows_archive(unsafe, tmp_path / "unsafe")

    duplicate = tmp_path / "duplicate.zip"
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(duplicate, "w") as bundle:
            bundle.writestr("MeluLauncher/MeluLauncher.exe", b"one")
            bundle.writestr("MeluLauncher/MeluLauncher.exe", b"two")
    with pytest.raises(InstallError, match="invalid"):
        LauncherUpdater()._extract_windows_archive(duplicate, tmp_path / "duplicate")

    linked = tmp_path / "linked.zip"
    link = zipfile.ZipInfo("MeluLauncher/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(linked, "w") as bundle:
        bundle.writestr(link, "target")
    with pytest.raises(InstallError, match="invalid"):
        LauncherUpdater()._extract_windows_archive(linked, tmp_path / "linked")


def test_windows_helper_waits_for_exit_and_restores_on_failure(tmp_path: Path):
    script = tmp_path / "replace.ps1"
    LauncherUpdater._write_windows_helper(script, tmp_path / "old", tmp_path / "new", 1234)
    contents = script.read_text(encoding="utf-8")
    assert "Wait-Process -Id 1234" in contents
    assert "Move-Item -LiteralPath $old -Destination $backup" in contents
    assert "Move-Item -LiteralPath $backup -Destination $old" in contents
    assert "Start-Process -FilePath $executable -PassThru" in contents
    assert "$started.HasExited" in contents
    assert "Remove-Item -LiteralPath $backup -Recurse -Force -ErrorAction Stop" in contents


def test_windows_apply_stages_before_scheduling_the_handover(tmp_path: Path, monkeypatch):
    archive = tmp_path / "update.zip"
    archive.write_bytes(b"update")
    current = tmp_path / "installed"
    current.mkdir()
    staged = tmp_path / "staged" / "MeluLauncher"
    staged.mkdir(parents=True)
    (staged / "MeluLauncher.exe").write_bytes(b"new")
    (staged / "_internal").mkdir()
    updater = LauncherUpdater()
    recorded = {}
    monkeypatch.setattr("core.updater.app_temp_root", lambda: tmp_path)
    monkeypatch.setattr("core.updater.platform_key", lambda: "windows")
    monkeypatch.setattr("core.updater.sys.executable", str(current / "MeluLauncher.exe"))
    monkeypatch.setattr(updater, "_extract_windows_archive", lambda got, staging: recorded.setdefault("extracted", (got, staging)) and staged)
    monkeypatch.setattr(updater, "_write_windows_helper", lambda script, old, new, pid: recorded.update(script=script, old=old, new=new, pid=pid))
    monkeypatch.setattr("core.updater.subprocess.Popen", lambda args, **kwargs: recorded.update(command=args, popen=kwargs))
    updater._apply_windows(archive)
    assert recorded["extracted"][0] == archive
    assert recorded["old"] == current
    assert recorded["new"] == staged
    assert recorded["script"].parent != current
    assert recorded["command"][-1] == str(recorded["script"])


def test_macos_helper_preserves_bundle_metadata_and_has_recovery(tmp_path: Path):
    script = tmp_path / "replace.sh"
    LauncherUpdater._write_macos_helper(script, Path("/Applications/MeluLauncher.app"), tmp_path / "update.zip", 99)
    contents = script.read_text(encoding="utf-8")
    assert "/usr/bin/ditto -x -k" in contents
    assert "while kill -0 99" in contents
    assert "test -x \"$candidate/Contents/MacOS/MeluLauncher\"" in contents
    assert 'mv "$backup" "$old"' in contents
