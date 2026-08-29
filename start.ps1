# 🛡️ BlinkSafe - Startup Script (Windows PowerShell)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Write-Host ""
    Write-Host "❌ ERROR: Python 3 is required to run BlinkSafe." -ForegroundColor Red
    Write-Host "Please install Python 3 from:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure 'Add Python to PATH' is enabled." -ForegroundColor Yellow
    Write-Host "Then run:" -ForegroundColor Yellow
    Write-Host ".\start.ps1" -ForegroundColor Cyan
    Write-Host ""
    Read-Host -Prompt "Press Enter to exit..."
    exit 1
}

if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment (venv)..." -ForegroundColor Cyan
    & $PythonCmd -m venv venv
}

if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

& $PythonCmd start.py $args
