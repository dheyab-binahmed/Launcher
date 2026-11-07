from __future__ import annotations

import json
from pathlib import Path


class Settings:
    # The manifest is a bundled build setting. Persisting it in a shared user
    # profile lets a previous production build override a testing build (or
    # vice versa), so only player preferences belong in this file.
    PERSISTED_KEYS = {"language", "ui_language"}

    def __init__(self, path: Path, defaults_path: Path | None = None) -> None:
        self.path = path
        self.data = {"language": "en", "manifest_url": ""}
        if defaults_path:
            try:
                defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
                if isinstance(defaults, dict): self.data.update(defaults)
            except (OSError, json.JSONDecodeError):
                pass
        self.load()

    def load(self) -> None:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update({key: value for key, value in loaded.items() if key in self.PERSISTED_KEYS})
        except (OSError, json.JSONDecodeError):
            pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        saved = {key: value for key, value in self.data.items() if key in self.PERSISTED_KEYS}
        self.path.write_text(json.dumps(saved, indent=2), encoding="utf-8")

    @property
    def language(self) -> str:
        return self.data.get("language", "en")

    @language.setter
    def language(self, value: str) -> None:
        self.data["language"] = value; self.save()
