#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt
python3 -m PyInstaller --noconfirm --clean --windowed --onedir --name MeluLauncher --add-data "config:config" main.py
echo "macOS launcher: dist/MeluLauncher/MeluLauncher.app"
