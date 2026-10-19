$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:OS -ne 'Windows_NT') { throw 'Run this build script on Windows.' }
py -3 -m venv .venv-build
if ($LASTEXITCODE -ne 0) { throw 'Cannot create build environment.' }
$python = Join-Path $PWD '.venv-build\Scripts\python.exe'
& $python -m pip install -r packaging/requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed.' }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx --name KixWare --paths . --add-data "packaging/licenses;licenses" kixware.py
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
$report = Join-Path $PWD 'dist\smoke-report.json'
if (Test-Path $report) { Remove-Item $report }
$process = Start-Process -FilePath (Join-Path $PWD 'dist\KixWare.exe') -ArgumentList @('--smoke-test', ('"' + $report + '"')) -PassThru
if (-not $process.WaitForExit(90000)) { $process.Kill(); throw 'Packaged smoke test timed out.' }
if ($process.ExitCode -ne 0) { throw 'Packaged smoke test failed.' }
if (-not (Test-Path $report)) { throw 'Packaged smoke test produced no report.' }
$result = Get-Content $report -Raw | ConvertFrom-Json
if ($result.status -ne 'passed' -or -not $result.frozen) { throw 'Packaged smoke test did not pass.' }
Copy-Item packaging/QUICKSTART.txt dist/QUICKSTART.txt
Compress-Archive -Path dist/KixWare.exe, dist/QUICKSTART.txt -DestinationPath dist/KixWare-Windows-x64.zip -Force
Get-FileHash dist/KixWare.exe -Algorithm SHA256 | Format-List
Write-Host 'Built and smoke-tested dist/KixWare-Windows-x64.zip'
