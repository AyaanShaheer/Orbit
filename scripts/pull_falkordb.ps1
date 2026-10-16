$maxRetries = 20
$attempt = 1
while ($attempt -le $maxRetries) {
    Write-Host "Pull attempt $attempt of $maxRetries..."
    docker pull falkordb/falkordb:latest
    if ($LASTEXITCODE -eq 0) {
        Write-Host "FalkorDB pull successful!"
        exit 0
    }
    Write-Host "Pull failed, retrying in 3 seconds..."
    Start-Sleep -Seconds 3
    $attempt++
}
exit 1
