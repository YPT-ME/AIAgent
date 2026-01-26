# Script para configurar o datasource ClickHouse no Grafana
Write-Host "Aguardando Grafana iniciar..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
$headers = @{
    "Authorization" = "Basic $auth"
    "Content-Type" = "application/json"
}

# Criar datasource
$datasource = @{
    name = "ClickHouse"
    type = "grafana-clickhouse-datasource"
    uid = "clickhouse"
    access = "proxy"
    isDefault = $true
    jsonData = @{
        defaultDatabase = "analytics"
        host = "clickhouse"
        port = 9000
        protocol = "native"
        secure = $false
        username = "analytics"
    }
    secureJsonData = @{
        password = "analytics_password"
    }
} | ConvertTo-Json -Depth 10

try {
    Write-Host "Criando datasource ClickHouse..." -ForegroundColor Yellow
    $result = Invoke-RestMethod -Uri "http://localhost:3002/api/datasources" -Method Post -Body $datasource -Headers $headers -ErrorAction Stop
    Write-Host "✓ Datasource criado com sucesso!" -ForegroundColor Green
    Write-Host "  ID: $($result.id)" -ForegroundColor Cyan
    Write-Host "  UID: $($result.uid)" -ForegroundColor Cyan
} catch {
    if ($_.Exception.Message -like "*409*" -or $_.ErrorDetails.Message -like "*already exists*") {
        Write-Host "✓ Datasource já existe!" -ForegroundColor Green
    } else {
        Write-Host "✗ Erro ao criar datasource: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host "Grafana está pronto!" -ForegroundColor Green
Write-Host "Acesse: http://localhost:3002" -ForegroundColor Cyan
Write-Host "Login: admin / admin" -ForegroundColor Cyan
Write-Host "Dashboard: RAG Agent Chat Analytics" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
