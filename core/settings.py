from __future__ import annotations

import json
from pathlib import Path


class Settings:
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
                # Older builds persisted an empty placeholder manifest URL. Do
                # not let it disable the verified bundled default after an
                # upgrade; a non-empty user URL is still respected.
                if not str(loaded.get("manifest_url", "")).strip():
                    loaded = {key: value for key, value in loaded.items() if key != "manifest_url"}
                self.data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    @property
    def language(self) -> str:
        return self.data.get("language", "en")

    @language.setter
    def language(self, value: str) -> None:
        self.data["language"] = value; self.save()
