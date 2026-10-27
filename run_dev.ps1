# DevSentinel One-Click Local Launcher (PowerShell)
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Starting DevSentinel Platform             " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan

$root = $PSScriptRoot

# 1. Start Backend in separate process
Write-Host "[1/2] Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.app.main:app --reload --port 8000" -WorkingDirectory $root -PassThru

Start-Sleep -Seconds 2

# 2. Start Frontend
Write-Host "[2/2] Starting Vite React Frontend on http://localhost:5173..." -ForegroundColor Yellow
Set-Location "$root\frontend"
npm run dev
