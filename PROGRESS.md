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

## Automated test result

`9 passed in 0.31s` using the isolated build environment. Coverage includes manifest parsing/rejection, published/unpublished language choice, SHA-256/size verification, version/revision comparison, missing menu file behavior, and chapter filtering.

## Pending / blocked by release inputs

* Public GitHub repository, stable HTTPS manifest URL, and immutable release assets.
* Real Russian, macOS, and chapter files with launch paths, hashes, and sizes.
* Full in-place self-replacement is staged by `core/updater.py`, but is not enabled in the UI until the final launcher release archive format and target installation policy are approved. This prevents replacing a running Windows EXE or a signed macOS bundle unsafely.
* macOS packaging/runtime testing requires GitHub Actions and a real Mac respectively; neither has been claimed as performed locally.
