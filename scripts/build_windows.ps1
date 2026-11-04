$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --windowed --onedir --name MeluLauncher --add-data "config;config" main.py
Write-Host "Windows launcher: dist\MeluLauncher\MeluLauncher.exe"
