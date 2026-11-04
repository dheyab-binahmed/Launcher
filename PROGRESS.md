# Progress report — 2026-11-04

## Completed and tested on Windows

* Preserved original menu files in the parent `menu` folder; no original file was modified.
* Inspected original Windows menu/PCK sizes and SHA-256 values.
* Modular PySide6 launcher UI with English/Russian UI strings and persisted game-language preference.
* HTTPS-only, schema-validated JSON manifest parsing.
* Background downloads to `.part`, retry/timeout handling, size/SHA-256 validation, and atomic final rename.
* Temp-directory installation organized by language/version/revision; Windows EXE/PCK are verified before launch and run with the required directory as CWD.
* Unpublished-language, network, malformed manifest, missing file, and integrity failures are shown as player-safe errors.
* Chapter availability filtering without invented chapter executable names.
* Windows PyInstaller onedir package built and process-start smoke-tested.
* Added a checked-in stable manifest for the published `menu-b1.0.0-r1` English Windows assets, using their independently verified names, sizes, and hashes.
* Launcher startup now fetches the manifest in a background worker. When it declares a newer verified launcher ZIP, the UI downloads it, verifies its size/SHA-256, starts a replacement helper, then closes. The helper waits for the old process, installs the complete package, and starts the new launcher.
* Windows update extraction validates the actual PyInstaller onedir layout (`MeluLauncher.exe` plus `_internal`). macOS update extraction is deferred to `/usr/bin/ditto` after exit, preserving application-bundle metadata and executable permissions.
* Replacement keeps a uniquely named sibling backup and restores it if moving or starting the replacement fails. A live update still cannot be exercised until a real launcher release ZIP is published in the manifest.
* Build scripts now create distributable ZIP archives; CI uploads those archives.

## Automated test result

`16 passed` using the isolated build environment. Coverage includes manifest parsing/rejection, published/unpublished language choice, SHA-256/size verification, version/revision comparison, missing menu file behavior, chapter filtering, the Windows onedir update ZIP layout, unsafe/incomplete update archives, and replacement-helper recovery scripts.

## Pending / blocked by release inputs

* Real Russian, macOS, and chapter files with launch paths, hashes, and sizes.
* The first launcher release assets (ZIP URL, byte size, and SHA-256) have not yet been published, so automatic launcher replacement cannot be exercised against a live release.
* macOS packaging is verified by GitHub Actions; runtime testing, signing, and notarization still require a real Mac and distribution decision.
