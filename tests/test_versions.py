import json

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
