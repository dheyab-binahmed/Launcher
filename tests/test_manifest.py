import json
from pathlib import Path
import pytest
from core.errors import ManifestError
from core.manifest import Manifest


def sample():
    return {"schema_version": 1, "launcher": {"version": "0.1.0", "assets": {"windows": {"url": "https://example.com/l.zip", "filename": "l.zip", "size": 1, "sha256": "a" * 64}}}, "menus": {"en": {"windows": {"available": True, "version": "b1", "revision": 2, "launch_path": "menu.exe", "artifacts": [{"url": "https://example.com/menu.exe", "filename": "menu.exe", "size": 1, "sha256": "b" * 64}, {"url": "https://example.com/menu.pck", "filename": "menu.pck", "size": 1, "sha256": "c" * 64}]}}}}


def test_manifest_parses_and_selects_release():
    result = Manifest.from_json(json.dumps(sample())).menu_for("en", "windows")
    assert (result.version, result.revision, len(result.artifacts)) == ("b1", 2, 2)


@pytest.mark.parametrize("mutator", [lambda d: d.update(schema_version=2), lambda d: d["menus"]["en"]["windows"].update(launch_path="../menu.exe"), lambda d: d["launcher"]["assets"]["windows"].update(url="http://bad")])
def test_invalid_manifest_rejected(mutator):
    data = sample(); mutator(data)
    with pytest.raises(ManifestError): Manifest.from_json(json.dumps(data))


def test_unpublished_language_explains_unavailability():
    data = sample(); data["menus"]["ru"] = {"windows": {"available": False}}
    with pytest.raises(ManifestError, match="not published"): Manifest.from_json(json.dumps(data)).menu_for("ru", "windows")
