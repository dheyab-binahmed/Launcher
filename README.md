# Melu Launcher

The original beta files remain untouched in the parent `menu` folder. This project downloads each menu into the operating system temporary directory (`%TEMP%\MeluLauncher` on Windows), separated by language, menu version, and revision. Temporary files can be purged by the operating system; the launcher will verify and download them again.

## Development and Windows build

This computer has Python 3.11 installed; the release workflows use the required Python 3.12. Install Python 3.12 locally, then from this directory run:

```powershell
py -3.12 -m pip install -r requirements.txt pytest
py -3.12 -m pytest tests -q
.\scripts\build_windows.ps1
```

The onedir executable will be at `dist\MeluLauncher\MeluLauncher.exe`. Do not move only the EXE: keep its generated PyInstaller directory together.

## Publishing a release

1. Create a public GitHub repository and upload the whole `Launcher` directory as its repository root (or adjust workflow artifact paths if it is a subdirectory).
2. Create a GitHub Release for each immutable asset set. Upload the launcher archives and menu assets. Do **not** overwrite an existing release asset.
3. Copy `examples/manifest.example.json` to a release asset named `manifest.json`, replace `OWNER/REPOSITORY`, every placeholder launcher hash/size, and URLs with the exact HTTPS GitHub Release asset URLs. The English Windows menu hashes and sizes are already calculated from the inspected original beta files.
4. Host `manifest.json` at a stable HTTPS URL (for example a version-controlled `raw.githubusercontent.com` URL) and set that URL in `config/settings.json` as `manifest_url` before building the launcher.
5. For a menu replacement that retains visible version `b1.0.0`, increment `revision`, publish new immutable assets, and change their size/hash/URLs in the manifest. The launcher detects revision and hash changes.

Russian entries are deliberately marked unavailable; no Russian game files were invented. Mark an entry available only after its real executable/archive, exact launch path, size, and SHA-256 are supplied.

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
