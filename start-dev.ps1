# start-dev.ps1
Write-Host "🔌 Starting SSH tunnel..."
Start-Process ssh -ArgumentList "-L 5433:127.0.0.1:5432 pen@100.118.33.12 -N" -WindowStyle Hidden

Start-Sleep -Seconds 2

Write-Host "🚀 Starting Docker..."
docker-compose up -d

Write-Host "✅ Dev environment ready!"
