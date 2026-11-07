# Melu Launcher

The original beta files remain untouched in the parent `menu` folder. This project downloads each menu into the operating system temporary directory (`%TEMP%\MeluLauncher` on Windows), separated by language, menu version, and revision. Temporary files can be purged by the operating system; the launcher will verify and download them again.

## Development and Windows build

Use a clean virtual environment for Windows builds. The requirements pin one compatible PySide6 Essentials/shiboken6/Qt runtime set, preventing PyInstaller from collecting DLLs from different Qt releases. The release workflows use Python 3.12; locally, from this directory run:

```powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements.txt pytest
.\.venv-build\Scripts\python.exe -m pytest tests -q
.\scripts\build_windows.ps1 -PythonExe .\.venv-build\Scripts\python.exe
```

The onedir executable will be at `dist\MeluLauncher\MeluLauncher.exe`. Do not move only the EXE: keep its generated PyInstaller directory together.

For an unmerged-branch test build only, the Windows script accepts an HTTPS manifest override without changing `config/settings.json`:

```powershell
.\scripts\build_windows.ps1 -ManifestUrl 'https://raw.githubusercontent.com/dheyab-binahmed/Launcher/codex/complete-windows-launcher/config/manifest.json'
```

The resulting ZIP is deliberately a testing artifact. Production builds retain the `main` raw-manifest URL in `config/settings.json`.

## Publishing a release

1. Create a public GitHub repository and upload the whole `Launcher` directory as its repository root (or adjust workflow artifact paths if it is a subdirectory).
2. Create a GitHub Release for each immutable asset set. Upload the launcher archives and menu assets. Do **not** overwrite an existing release asset.
3. `config/manifest.json` is the live manifest source. It already references the verified published English Windows beta. Do not alter those menu values. It deliberately has no launcher asset until the first verified launcher ZIP is published.
4. Build the launcher archive, calculate its exact byte count and SHA-256, upload it to an immutable GitHub Release, then add its URL, filename, size, and hash under `launcher.assets.windows` (and/or `macos`). Commit the manifest change to `main`; the shipped launcher reads it from the stable `raw.githubusercontent.com` URL configured in `config/settings.json`.
5. For a menu replacement that retains visible version `b1.0.0`, increment `revision`, publish new immutable assets, and change their size/hash/URLs in the manifest. The launcher detects revision and hash changes.

Russian entries are deliberately marked unavailable; no Russian game files were invented. Mark an entry available only after its real executable/archive, exact launch path, size, and SHA-256 are supplied.

## Launcher updates

At startup, the launcher checks the manifest in a background worker. If `launcher.version` is newer and contains an asset for the current platform, it downloads the HTTPS ZIP through the normal `.part` download path, verifies its exact size and SHA-256, and then asks the UI to close.

The replacement helper waits for the old process to exit before changing files. On Windows it validates and extracts the `MeluLauncher/` PyInstaller onedir ZIP (including `_internal`), moves the old installation to a uniquely named sibling backup, moves in the new directory, and starts `MeluLauncher.exe`. If moving or starting fails, it restores the backup. On macOS the helper uses `/usr/bin/ditto` after exit so the downloaded `.app` retains executable permissions and bundle metadata; it validates the app executable before replacing the old bundle and restores the backup on failure.

The helper retains the backup through the replacement startup check, restores it if replacement fails, and safely removes it after a successful handoff. This code path is connected to the UI, but it will remain dormant until a real launcher ZIP and its immutable URL, byte size, and SHA-256 are placed in the manifest. It has not yet been exercised against a published launcher release or on a physical Mac.

## Manifest rules

Only HTTPS downloads are accepted. Every artifact needs `url`, basename-only `filename`, exact byte `size`, and 64-character SHA-256. The Windows release must list both the Godot EXE and PCK and uses the EXE filename as `launch_path`; the launcher verifies both before starting with the menu folder as working directory. macOS should contain a complete verified ZIP/app archive and a launch path inside it—do not replace a signed app’s internal PCK.

## Chapters

No chapter executable or launch instruction was present in the supplied folder, so there is no fabricated chapter launcher. `core/chapter_manager.py` filters real manifest chapter records by language/platform. To enable chapters, provide the actual per-platform artifact layout and a verified launch path, then extend the manifest schema and Godot menu integration. The supplied Godot menu only highlights Chapter 1; it does not launch Ren'Py according to the provided inspection notes.

## macOS checklist for a supervisor

CI confirms that the Python app packages, but it is not runtime testing. On a physical Intel and/or Apple Silicon Mac: download the macOS artifact, open the `.app`, select English, confirm it downloads and launches the verified complete `.app` archive, relaunch offline after install, corrupt/delete a downloaded file and confirm redownload, test update failure, and test a newer revision. Because the menu app is ad-hoc signed and not notarized, Gatekeeper may require Control-click → Open or organizational signing/notarization before public distribution.

## Known input still required

* The public GitHub repository and stable HTTPS manifest URL.
* Real Russian menu assets (and macOS archive), release URLs, hashes, sizes, and launch paths.
* Real chapter executables/archives and menu-to-chapter integration instructions.
* A macOS device for runtime test and signing/notarization decisions.
