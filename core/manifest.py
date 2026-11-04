from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse

from .errors import ManifestError

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def _fail(message: str) -> None:
    raise ManifestError(f"Invalid manifest: {message}")


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{field} must be a non-empty string")
    return value


def _url(value: Any, field: str) -> str:
    result = _string(value, field)
    parsed = urlparse(result)
    if parsed.scheme != "https" or not parsed.netloc:
        _fail(f"{field} must be an HTTPS URL")
    return result


@dataclass(frozen=True)
class Artifact:
    url: str
    size: int
    sha256: str
    filename: str

    @classmethod
    def parse(cls, data: Any, field: str) -> "Artifact":
        if not isinstance(data, dict):
            _fail(f"{field} must be an object")
        size = data.get("size")
        checksum = data.get("sha256")
        filename = _string(data.get("filename"), f"{field}.filename")
        if PurePosixPath(filename).name != filename or filename in {".", ".."}:
            _fail(f"{field}.filename must not contain a path")
        if not isinstance(size, int) or size < 1:
            _fail(f"{field}.size must be a positive integer")
        if not isinstance(checksum, str) or not HEX64.fullmatch(checksum):
            _fail(f"{field}.sha256 must be a SHA-256 hex digest")
        return cls(_url(data.get("url"), f"{field}.url"), size, checksum.lower(), filename)


@dataclass(frozen=True)
class MenuRelease:
    language: str
    available: bool
    version: str | None = None
    revision: int | None = None
    artifacts: tuple[Artifact, ...] = ()
    launch_path: str | None = None


@dataclass(frozen=True)
class Manifest:
    schema_version: int
    launcher_version: str
    launcher: dict[str, Artifact]
    menus: dict[str, dict[str, MenuRelease]]
    chapters: list[dict[str, Any]]

    @classmethod
    def from_json(cls, raw: str) -> "Manifest":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ManifestError("Invalid JSON.") from error
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            _fail("schema_version must be 1")
        launcher = data.get("launcher")
        if not isinstance(launcher, dict):
            _fail("launcher must be an object")
        assets = launcher.get("assets")
        if not isinstance(assets, dict):
            _fail("launcher.assets must be an object")
        parsed_launcher = {key: Artifact.parse(value, f"launcher.assets.{key}") for key, value in assets.items() if key in {"windows", "macos"}}
        if not parsed_launcher:
            _fail("launcher.assets needs at least one supported platform")
        menus_raw = data.get("menus")
        if not isinstance(menus_raw, dict):
            _fail("menus must be an object")
        menus: dict[str, dict[str, MenuRelease]] = {}
        for language, platforms in menus_raw.items():
            if not isinstance(language, str) or not isinstance(platforms, dict):
                _fail("menus must map language codes to platform objects")
            menus[language] = {}
            for platform_name, release in platforms.items():
                if platform_name not in {"windows", "macos"} or not isinstance(release, dict):
                    _fail("unsupported menu platform or malformed release")
                available = release.get("available", False)
                if not isinstance(available, bool):
                    _fail("menu availability must be boolean")
                if not available:
                    menus[language][platform_name] = MenuRelease(language, False)
                    continue
                revision = release.get("revision")
                artifact_data = release.get("artifacts")
                launch_path = _string(release.get("launch_path"), "menu.launch_path")
                if not isinstance(revision, int) or revision < 1 or not isinstance(artifact_data, list) or not artifact_data:
                    _fail("available menu needs a positive revision and artifacts")
                if PurePosixPath(launch_path).is_absolute() or ".." in PurePosixPath(launch_path).parts:
                    _fail("menu.launch_path is unsafe")
                parsed = tuple(Artifact.parse(item, "menu.artifacts") for item in artifact_data)
                if platform_name == "windows" and len(parsed) < 2:
                    _fail("Windows menu needs EXE and PCK artifacts")
                menus[language][platform_name] = MenuRelease(language, True, _string(release.get("version"), "menu.version"), revision, parsed, launch_path)
        chapters = data.get("chapters", [])
        if not isinstance(chapters, list):
            _fail("chapters must be a list")
        return cls(1, _string(launcher.get("version"), "launcher.version"), parsed_launcher, menus, chapters)

    def menu_for(self, language: str, platform: str) -> MenuRelease:
        release = self.menus.get(language, {}).get(platform)
        if release is None or not release.available:
            raise ManifestError(f"The {language.upper()} menu is not published for this platform yet.")
        return release
