#!/usr/bin/env pwsh
# TenderSense AI — Quick Start Script
# Run from repo root: .\start.ps1

$RepoRoot = $PSScriptRoot

Write-Host "🚀 Starting TenderSense AI..." -ForegroundColor Cyan

# Backend
Write-Host "`n📦 Installing backend dependencies..." -ForegroundColor Yellow
Set-Location "$RepoRoot\backend"
python -m pip install -r requirements.txt --quiet

Write-Host "🔧 Checking .env file..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Created .env from template. Please fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENROUTER_API_KEY" -ForegroundColor Red
}

Write-Host "🌐 Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -WorkingDirectory "$RepoRoot\backend" -ArgumentList "-NoExit", "-Command", "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

# Frontend
Write-Host "`n📦 Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location "$RepoRoot\frontend\tendersense-ai-insights"
npm install --silent

Write-Host "🌐 Starting Vite dev server on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -WorkingDirectory "$RepoRoot\frontend\tendersense-ai-insights" -ArgumentList "-NoExit", "-Command", "npm run dev"

Set-Location $RepoRoot

Write-Host "`n✅ Both servers starting..." -ForegroundColor Green
Write-Host "   Backend: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "`n📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Fill in backend/.env with your Supabase + OpenRouter credentials"
Write-Host "   2. Run database/schema.sql in Supabase SQL Editor"
Write-Host "   3. Create storage buckets: tender-documents, bidder-documents"
Write-Host "   4. Upload a tender PDF and run evaluation!"
