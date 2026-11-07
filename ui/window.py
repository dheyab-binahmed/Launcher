from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from core.launcher import MenuService
from core.settings import Settings
from core.updater import LauncherUpdater
from ui.language import TEXT

LAUNCHER_VERSION = "0.1.0"


def player_error(message: str, text: dict[str, str]) -> str:
    """Map known safe service failures to a precise player-facing message."""
    lower = message.lower()
    if "invalid json" in lower or "invalid manifest" in lower:
        return text["manifest_invalid"]
    if "not published" in lower:
        return text["release_unavailable"]
    if "release manifest" in lower or "manifest is unavailable" in lower:
        return text["manifest_unavailable"]
    if "size check" in lower:
        return text["size_error"]
    if "sha-256" in lower or "integrity" in lower:
        return text["sha_error"]
    if "timed out" in lower:
        return text["timeout_error"]
    if "not enough disk space" in lower or "not enough space" in lower or "no space left" in lower:
        return text["disk_error"]
    if "download" in lower:
        return text["download_error"]
    if "install" in lower or "archive" in lower or "launch file" in lower:
        return text["install_error"]
    return message


class Worker(QObject):
    status = Signal(str)
    progress = Signal(int, int)
    completed = Signal(str, int)
    update_ready = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, language: str) -> None:
        super().__init__()
        self.url, self.language = url, language

    def run(self) -> None:
        try:
            service = MenuService()
            manifest = service.manifest(self.url)
            updater = LauncherUpdater()
            artifact = updater.available(manifest, LAUNCHER_VERSION)
            if artifact:
                self.status.emit("Downloading launcher update…")
                self.update_ready.emit(str(updater.stage(artifact)))
                return
            from core.platform_utils import platform_key
            release = manifest.menu_for(self.language, platform_key())
            executable = service.install(release, platform_key(), self.progress.emit, self.status.emit)
            service.launch(executable, platform_key())
            self.completed.emit(release.version or "", release.revision or 0)
        except Exception as error:
            self.failed.emit(str(error))


class UpdateCheckWorker(QObject):
    """Fetches only the small manifest at startup; it never starts a game."""
    update_ready = Signal(str)
    no_update = Signal()
    failed = Signal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            manifest = MenuService().manifest(self.url)
            artifact = LauncherUpdater().available(manifest, LAUNCHER_VERSION)
            if artifact:
                self.update_ready.emit(str(LauncherUpdater().stage(artifact)))
            else:
                self.no_update.emit()
        except Exception as error:
            self.failed.emit(str(error))


class LauncherWindow(QMainWindow):
    def __init__(self, settings_path: Path, defaults_path: Path) -> None:
        super().__init__()
        self.settings = Settings(settings_path, defaults_path)
        self.ui_language = self.settings.data.get("ui_language", self.settings.language)
        if self.ui_language not in TEXT:
            self.ui_language = "en"
        self.setMinimumSize(660, 580)
        self.resize(760, 650)
        self._build()
        self._refresh()
        if self._has_manifest():
            QTimer.singleShot(0, self._check_for_update)

    def _build(self) -> None:
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(42, 36, 42, 36); outer.setSpacing(18)
        self.title = QLabel(); self.title.setObjectName("title"); self.title.setAlignment(Qt.AlignCenter); outer.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("subtitle"); self.subtitle.setAlignment(Qt.AlignCenter); outer.addWidget(self.subtitle)

        language_card = QFrame(); language_card.setObjectName("card")
        language_layout = QVBoxLayout(language_card); language_layout.setContentsMargins(24, 20, 24, 22); language_layout.setSpacing(12)
        self.interface_label = QLabel(); self.interface_label.setObjectName("section"); language_layout.addWidget(self.interface_label)
        choices = QHBoxLayout(); choices.setSpacing(12)
        self.english_button, self.russian_button = QPushButton(), QPushButton()
        self.language_group = QButtonGroup(self); self.language_group.setExclusive(True)
        for button, code in ((self.english_button, "en"), (self.russian_button, "ru")):
            button.setCheckable(True); button.setMinimumHeight(50); button.setProperty("code", code)
            self.language_group.addButton(button); choices.addWidget(button)
        self.language_group.buttonClicked.connect(self._set_language)
        language_layout.addLayout(choices)
        self.content_label = QLabel(); self.content_label.setObjectName("hint"); self.content_label.setWordWrap(True); language_layout.addWidget(self.content_label)
        outer.addWidget(language_card)

        self.status_card = QFrame(); self.status_card.setObjectName("statusCard")
        status_layout = QVBoxLayout(self.status_card); status_layout.setContentsMargins(24, 20, 24, 20); status_layout.setSpacing(10)
        self.status_heading = QLabel(); self.status_heading.setObjectName("statusHeading"); status_layout.addWidget(self.status_heading)
        self.status = QLabel(); self.status.setObjectName("status"); self.status.setWordWrap(True); self.status.setMinimumHeight(52); status_layout.addWidget(self.status)
        self.progress = QProgressBar(); self.progress.setMinimumHeight(22); self.progress.setTextVisible(True); status_layout.addWidget(self.progress)
        outer.addWidget(self.status_card)
        self.play = QPushButton(); self.play.setObjectName("play"); self.play.setMinimumHeight(58); self.play.clicked.connect(self._play); outer.addWidget(self.play)
        outer.addStretch(1)
        self.versions = QLabel(); self.versions.setObjectName("versions"); self.versions.setAlignment(Qt.AlignCenter); self.versions.setWordWrap(True); outer.addWidget(self.versions)
        self.setStyleSheet("""
            #root { background: #0b1220; color: #f8fafc; }
            QLabel { font-family: "Segoe UI", "Arial", sans-serif; }
            QLabel#title { color: #f8fafc; font-size: 34px; font-weight: 700; }
            QLabel#subtitle { color: #b9c8da; font-size: 13px; font-weight: 600; letter-spacing: 2px; }
            QFrame#card, QFrame#statusCard { background: #162235; border: 1px solid #2d405a; border-radius: 12px; }
            QFrame#statusCard { border-color: #285f78; }
            QLabel#section { color: #f1f5f9; font-size: 15px; font-weight: 700; }
            QLabel#hint { color: #c9d5e4; font-size: 14px; }
            QLabel#statusHeading { color: #8be9fd; font-size: 15px; font-weight: 700; }
            QLabel#status { color: #f1f5f9; font-size: 15px; }
            QLabel#versions { color: #b9c8da; font-size: 13px; }
            QPushButton { background: #26364e; border: 1px solid #6d87a8; border-radius: 8px; color: #ffffff; font-family: "Segoe UI", "Arial", sans-serif; font-size: 16px; font-weight: 600; padding: 10px 18px; }
            QPushButton:hover { background: #344b69; border-color: #8be9fd; }
            QPushButton:checked { background: #0e7490; border: 2px solid #8be9fd; }
            QPushButton:disabled { background: #253246; border-color: #3b4b61; color: #9bacc0; }
            QPushButton#play { background: #0e91b5; border: 1px solid #a5f3fc; color: #ffffff; font-size: 19px; font-weight: 700; }
            QPushButton#play:hover { background: #16a8cc; }
            QProgressBar { background: #0d1726; border: 1px solid #526a88; border-radius: 6px; color: #ffffff; font-size: 12px; text-align: center; }
            QProgressBar::chunk { background: #22b8cf; border-radius: 5px; }
        """)

    def _has_manifest(self) -> bool:
        return bool(str(self.settings.data.get("manifest_url", "")).strip())

    def _refresh(self) -> None:
        text = TEXT[self.ui_language]
        selected = text["english"] if self.ui_language == "en" else text["russian"]
        self.setWindowTitle(text["title"]); self.title.setText(text["title"]); self.subtitle.setText(text["subtitle"])
        self.interface_label.setText(text["interface_language"]); self.english_button.setText(text["english"]); self.russian_button.setText(text["russian"])
        (self.english_button if self.ui_language == "en" else self.russian_button).setChecked(True)
        self.content_label.setText(f"{text['content_language']}\n{text['content_follows'].format(language=selected)}")
        self.play.setText(text["play"])
        configured = self._has_manifest(); self.play.setEnabled(configured)
        self.status_heading.setText(text["launcher"] if configured else text["setup_title"])
        self.status.setText(text["ready"] if configured else text["setup_message"])
        self.progress.setValue(0)
        self.versions.setText(f"{text['launcher']} {LAUNCHER_VERSION}  •  {text['menu']}: {'—' if configured else text['not_available']}")

    def _set_language(self, button: QPushButton) -> None:
        language = str(button.property("code"))
        self.ui_language = language
        # Current releases follow the selected launcher language; this is intentionally one choice.
        self.settings.data["ui_language"] = language; self.settings.data["language"] = language; self.settings.save()
        self._refresh()

    def _play(self) -> None:
        if not self._has_manifest(): self._refresh(); return
        self.play.setEnabled(False); self.progress.setValue(0)
        self.thread = QThread(self); self.worker = Worker(self.settings.data["manifest_url"], self.settings.language)
        self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.status.setText); self.worker.progress.connect(self._update_progress)
        self.worker.update_ready.connect(self._install_update)
        self.worker.completed.connect(self._done); self.worker.failed.connect(self._failed)
        self.worker.completed.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit)
        self.worker.update_ready.connect(self.thread.quit)
        self.thread.finished.connect(lambda: self.play.setEnabled(True)); self.thread.start()

    def _check_for_update(self) -> None:
        self.update_thread = QThread(self)
        self.update_worker = UpdateCheckWorker(self.settings.data["manifest_url"])
        self.update_worker.moveToThread(self.update_thread)
        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.update_ready.connect(self._install_update)
        self.update_worker.no_update.connect(lambda: self.status.setText(TEXT[self.ui_language]["ready"]))
        # A background update check must not block the player from starting a
        # cached or otherwise available menu.
        self.update_worker.failed.connect(lambda _message: None)
        self.update_worker.update_ready.connect(self.update_thread.quit)
        self.update_worker.no_update.connect(self.update_thread.quit)
        self.update_worker.failed.connect(self.update_thread.quit)
        self.update_thread.start()

    def _install_update(self, archive: str) -> None:
        try:
            self.status.setText(TEXT[self.ui_language]["updating"])
            LauncherUpdater().apply_and_restart(Path(archive))
            QApplication.quit()
        except Exception as error:
            self._failed(str(error))

    def _update_progress(self, value: int, total: int) -> None:
        self.progress.setValue(int(value * 100 / total) if total else 0)

    def _done(self, version: str, revision: int) -> None:
        self.status.setText(TEXT[self.ui_language]["started"].format(version=version, revision=revision)); self.progress.setValue(100)

    def _failed(self, message: str) -> None:
        text = TEXT[self.ui_language]
        message = player_error(message, text)
        self.status.setText(message); QMessageBox.warning(self, text["error_title"], message)


def run(settings_path: Path, defaults_path: Path) -> int:
    app = QApplication([]); app.setApplicationName("Launcher"); app.setFont(QFont("Segoe UI", 10))
    window = LauncherWindow(settings_path, defaults_path); window.show()
    return app.exec()
