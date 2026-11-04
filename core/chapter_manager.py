from __future__ import annotations

from typing import Any


class ChapterManager:
    """Manifest-facing chapter availability layer; no executable path is invented."""
    @staticmethod
    def available(chapters: list[dict[str, Any]], language: str, platform: str) -> list[dict[str, Any]]:
        return [item for item in chapters if item.get("language") == language and item.get("platform") == platform and item.get("available") is True]
