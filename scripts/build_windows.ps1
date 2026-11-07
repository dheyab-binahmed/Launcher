param(
    [string]$ManifestUrl = '',
    [string]$PythonExe = 'python'
)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
& $PythonExe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$configSource = 'config'
if ($ManifestUrl) {
    if ($ManifestUrl -notmatch '^https://') { throw 'ManifestUrl must use HTTPS.' }
    $configSource = Join-Path 'build' 'testing-config'
    New-Item -ItemType Directory -Path $configSource -Force | Out-Null
    Copy-Item -LiteralPath 'config\settings.json' -Destination (Join-Path $configSource 'settings.json') -Force
    $settingsPath = Join-Path $configSource 'settings.json'
    $settings = Get-Content -Raw -LiteralPath $settingsPath | ConvertFrom-Json
    $settings.manifest_url = $ManifestUrl
    $settings | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding utf8
}
# Keep generated specs under build/ so a testing build cannot leave the
# tracked production spec pointing at its temporary override configuration.
$configSourcePath = (Resolve-Path -LiteralPath $configSource).Path
& $PythonExe -m PyInstaller --noconfirm --clean --specpath build --windowed --onedir --name MeluLauncher --add-data "$configSourcePath;config" main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
if (Test-Path dist\MeluLauncher-windows.zip) { Remove-Item -LiteralPath dist\MeluLauncher-windows.zip }
Compress-Archive -Path dist\MeluLauncher -DestinationPath dist\MeluLauncher-windows.zip
Write-Host "Windows launcher: dist\MeluLauncher\MeluLauncher.exe"
Write-Host "Windows release archive: dist\MeluLauncher-windows.zip"
