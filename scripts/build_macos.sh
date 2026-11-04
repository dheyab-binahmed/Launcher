#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt
python3 -m PyInstaller --noconfirm --clean --windowed --onedir --name MeluLauncher --add-data "config:config" main.py
rm -f dist/MeluLauncher-macos.zip
ditto -c -k --sequesterRsrc --keepParent dist/MeluLauncher.app dist/MeluLauncher-macos.zip
echo "macOS launcher: dist/MeluLauncher.app"
echo "macOS release archive: dist/MeluLauncher-macos.zip"
