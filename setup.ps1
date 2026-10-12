$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host "TREN LOCAL - FIRST-TIME SETUP" -ForegroundColor Green
Write-Host "This installs Python and Ollama if needed, then downloads a local AI model (~5.2 GB)."
Write-Host "No API key or paid AI subscription is required."
function Find-Python {
    $fixedPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if (Test-Path $fixedPython) { return @($fixedPython) }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -c "import sys; assert sys.version_info >= (3,11)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @('py', '-3') }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; assert sys.version_info >= (3,11)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @('python') }
    }
    return @()
}
$pythonCommand = @(Find-Python)
if ($pythonCommand.Count -eq 0) {
    if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'Install Python 3.11+ from https://www.python.org/downloads/windows/ and rerun setup.bat. Enable the Python launcher in the installer.'
    }
    & winget install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Python installation did not complete. Install Python manually, then rerun setup.' }
    $pythonCommand = @(Find-Python)
    if ($pythonCommand.Count -eq 0) { throw 'Python was installed. Close this window and rerun setup.bat so PATH can refresh.' }
}
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
if (!(Test-Path $ollamaExe)) {
    $found = Get-Command ollama -ErrorAction SilentlyContinue
    if ($found) { $ollamaExe = $found.Source }
    else {
        if (!(Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install Ollama from https://ollama.com/download/windows and rerun setup.bat.' }
        & winget install --id Ollama.Ollama --exact --source winget --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { throw 'Ollama installation did not complete. Install it manually and rerun setup.' }
        if (!(Test-Path $ollamaExe)) { throw 'Ollama was installed. Close this window, open Ollama, and rerun setup.bat.' }
    }
}
# Disable optional cloud features for the Ollama process launched by this setup.
$env:OLLAMA_NO_CLOUD = '1'
$localModel = $env:TREN_MODEL
if (!$localModel) { $localModel = 'qwen3:8b' }
$online = $false
try { Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 | Out-Null; $online = $true } catch {}
if (!$online) {
    Start-Process $ollamaExe -ArgumentList 'serve' -WindowStyle Minimized
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try { Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 | Out-Null; $online = $true; break } catch {}
    }
}
if (!$online) { throw 'Ollama did not start. Open Ollama from the Start menu, then rerun setup.' }
Write-Host "Downloading $localModel. Keep this window open; download time depends on your connection." -ForegroundColor Cyan
& $ollamaExe pull $localModel
if ($LASTEXITCODE -ne 0) { throw 'Model download failed. Rerun setup.bat to resume it.' }
Write-Host "Setup complete. Double-click start.bat, then enter the pairing code shown in its window." -ForegroundColor Green
Write-Host "After PC chat works, follow PHONE-SETUP.md to connect your phone."
