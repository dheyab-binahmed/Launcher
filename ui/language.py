"""All player-facing launcher strings, kept separate from download logic."""

TEXT = {
    "en": {
        "title": "Launcher", "subtitle": "GAME LAUNCHER", "interface_language": "LAUNCHER INTERFACE LANGUAGE",
        "english": "English", "russian": "Русский", "content_language": "GAME CONTENT LANGUAGE",
        "content_follows": "Follows the selected launcher language: {language}", "play": "PLAY",
        "setup_title": "Release setup pending", "setup_message": "This launcher is waiting for its release configuration. Game files are not available until a release manifest has been configured.",
        "ready": "Ready to check for updates and launch the selected game content.", "launcher": "Launcher", "menu": "Menu", "not_available": "Not available",
        "started": "Started {version}, revision {revision}.", "error_title": "Launcher",
        "network_error": "Could not reach the release service. Check your internet connection and try again.",
        "download_error": "The download could not be completed. Please check your connection and try again.",
        "integrity_error": "The downloaded file did not pass its security check. It was not opened.",
    },
    "ru": {
        "title": "Лаунчер", "subtitle": "ИГРОВОЙ ЛАУНЧЕР", "interface_language": "ЯЗЫК ИНТЕРФЕЙСА ЛАУНЧЕРА",
        "english": "English", "russian": "Русский", "content_language": "ЯЗЫК ИГРОВОГО КОНТЕНТА",
        "content_follows": "Соответствует выбранному языку лаунчера: {language}", "play": "ИГРАТЬ",
        "setup_title": "Настройка релиза ожидается", "setup_message": "Этот лаунчер ожидает настройки релиза. Игровые файлы будут доступны после добавления манифеста релиза.",
        "ready": "Готов проверить обновления и запустить выбранный игровой контент.", "launcher": "Лаунчер", "menu": "Меню", "not_available": "Недоступно",
        "started": "Запущено: {version}, редакция {revision}.", "error_title": "Лаунчер",
        "network_error": "Не удалось связаться со службой релизов. Проверьте подключение к интернету и повторите попытку.",
        "download_error": "Не удалось завершить загрузку. Проверьте подключение и повторите попытку.",
        "integrity_error": "Загруженный файл не прошёл проверку безопасности и не был открыт.",
    },
}
