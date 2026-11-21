# Lance FreshRotten Guard en local (sans Docker) : backend sur :8000, frontend sur :5173.
# Usage : powershell -ExecutionPolicy Bypass -File .\dev.ps1
$racine = $PSScriptRoot
$env:TF_CPP_MIN_LOG_LEVEL = "2"
Start-Process -FilePath "$racine\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory "$racine\backend"
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev", "--", "--host", "127.0.0.1" -WorkingDirectory "$racine\frontend"
Write-Host "Backend : http://127.0.0.1:8000/docs  -  Application : http://127.0.0.1:5173"
