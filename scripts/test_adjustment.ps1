$ErrorActionPreference='Stop'

$login = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/auth/login' -Method Post -Body (ConvertTo-Json @{username='hooren_admin'; password='Hooren@2026#Secure'}) -ContentType 'application/json' -UseBasicParsing
$token = $login.access_token
Write-Output "TOKEN: $token"

$items = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/inventory/items' -Headers @{Authorization = "Bearer $token"} -UseBasicParsing
$branches = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/branches' -Headers @{Authorization = "Bearer $token"} -UseBasicParsing

if (-not $items -or -not $branches) {
    Write-Output "No items or branches available to test."
    exit 1
}

$branchId = $branches[0].id
$godowns = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/branches/$branchId/godowns" -Headers @{Authorization = "Bearer $token"} -UseBasicParsing
$itemId = $items[0].id

$payload = @{
    branch_id = $branchId
    godown_id = $godowns[0].id
    adjustment_date = (Get-Date).ToString('yyyy-MM-dd')
    reason = 'api-test'
    items = @(
        @{ item_id = $itemId; difference = 0.001; unit_cost = 1.0 }
    )
}

Write-Output "PAYLOAD:"; $payload | ConvertTo-Json -Depth 5

try {
    $resp = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/inventory/stock/adjustment' -Method Post -Headers @{Authorization = "Bearer $token"} -Body ($payload | ConvertTo-Json -Depth 5) -ContentType 'application/json' -UseBasicParsing
    Write-Output "RESPONSE:"; $resp | ConvertTo-Json -Depth 5
} catch {
    Write-Output "ERROR:"; $_.Exception.Message
    if ($_.Exception.Response -ne $null) {
        try { $_.Exception.Response.Content | Write-Output } catch {}
    }
    exit 1
}
