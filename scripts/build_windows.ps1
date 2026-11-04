$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --windowed --onedir --name MeluLauncher --add-data "config;config" main.py
if (Test-Path dist\MeluLauncher-windows.zip) { Remove-Item -LiteralPath dist\MeluLauncher-windows.zip }
Compress-Archive -Path dist\MeluLauncher -DestinationPath dist\MeluLauncher-windows.zip
Write-Host "Windows launcher: dist\MeluLauncher\MeluLauncher.exe"
Write-Host "Windows release archive: dist\MeluLauncher-windows.zip"
