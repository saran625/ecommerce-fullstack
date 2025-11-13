# GitHub Secret Diagnostic Script
# This checks if your key will work in GitHub Actions
# Save as: diagnose-secret.ps1

$pemFile = "C:\Users\Admin\OneDrive\Desktop\ecommerce-fullstack\newkeypair.pem"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  GitHub Secret Format Diagnostic" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Read the key
$keyContent = Get-Content $pemFile -Raw

Write-Host "1. Checking key format..." -ForegroundColor Cyan
Write-Host ""

# Show first and last lines
$lines = Get-Content $pemFile
Write-Host "First line: $($lines[0])" -ForegroundColor White
Write-Host "Last line: $($lines[-1])" -ForegroundColor White
Write-Host "Total lines: $($lines.Count)" -ForegroundColor White
Write-Host ""

# Check for Windows line endings
if ($keyContent -match "`r`n") {
    Write-Host "WARNING: Key has Windows line endings (CRLF)" -ForegroundColor Yellow
    Write-Host "Converting to Unix line endings (LF)..." -ForegroundColor Cyan
    $keyContent = $keyContent -replace "`r`n", "`n"
    Write-Host "FIXED: Converted to Unix line endings" -ForegroundColor Green
} else {
    Write-Host "GOOD: Key already has Unix line endings" -ForegroundColor Green
}
Write-Host ""

# Check for trailing whitespace
if ($keyContent -match "[ \t]+`n" -or $keyContent -match "[ \t]+$") {
    Write-Host "WARNING: Key has trailing whitespace" -ForegroundColor Yellow
    $keyContent = $keyContent -replace "[ \t]+`n", "`n"
    $keyContent = $keyContent.TrimEnd()
    Write-Host "FIXED: Removed trailing whitespace" -ForegroundColor Green
} else {
    Write-Host "GOOD: No trailing whitespace" -ForegroundColor Green
}
Write-Host ""

# Check for leading/trailing blank lines
$trimmedKey = $keyContent.Trim()
if ($keyContent.Length -ne $trimmedKey.Length) {
    Write-Host "WARNING: Key has leading/trailing blank lines" -ForegroundColor Yellow
    $keyContent = $trimmedKey
    Write-Host "FIXED: Removed blank lines" -ForegroundColor Green
} else {
    Write-Host "GOOD: No extra blank lines" -ForegroundColor Green
}
Write-Host ""

# Verify structure
$hasBegin = $keyContent -match "^-----BEGIN"
$hasEnd = $keyContent -match "-----END.*-----$"

if ($hasBegin -and $hasEnd) {
    Write-Host "GOOD: Key structure is valid" -ForegroundColor Green
} else {
    Write-Host "ERROR: Key structure is invalid!" -ForegroundColor Red
    if (-not $hasBegin) { Write-Host "  Missing BEGIN marker at start" -ForegroundColor Yellow }
    if (-not $hasEnd) { Write-Host "  Missing END marker at end" -ForegroundColor Yellow }
}
Write-Host ""

# Save cleaned version
$cleanedFile = "$pemFile.cleaned"
$keyContent | Out-File -FilePath $cleanedFile -Encoding ASCII -NoNewline
Write-Host "Saved cleaned version to: $cleanedFile" -ForegroundColor Cyan
Write-Host ""

# Copy cleaned version to clipboard
$keyContent | Set-Clipboard
Write-Host "========================================" -ForegroundColor Green
Write-Host "  CLEANED KEY COPIED TO CLIPBOARD!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Key statistics:" -ForegroundColor Yellow
Write-Host "  Original size: $($keyContent.Length) bytes" -ForegroundColor White
Write-Host "  Lines: $($lines.Count)" -ForegroundColor White
Write-Host "  First char: $([int]$keyContent[0]) (should be 45 for '-')" -ForegroundColor White
Write-Host "  Last char: $([int]$keyContent[-1]) (should be 45 for '-')" -ForegroundColor White
Write-Host ""

# Test the cleaned key locally
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Testing Cleaned Key Locally" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

Write-Host "Saving cleaned key temporarily..." -ForegroundColor Cyan
$testKeyFile = "$env:TEMP\test_key.pem"
$keyContent | Out-File -FilePath $testKeyFile -Encoding ASCII -NoNewline

# Set permissions
Write-Host "Setting permissions..." -ForegroundColor Cyan
icacls $testKeyFile /inheritance:r | Out-Null
icacls $testKeyFile /grant:r "$($env:USERNAME):(R)" | Out-Null

Write-Host "Testing SSH with cleaned key..." -ForegroundColor Cyan
$testResult = ssh -i $testKeyFile -o StrictHostKeyChecking=no ubuntu@3.84.242.4 "echo 'Test successful'" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Cleaned key works!" -ForegroundColor Green
    Write-Host "Result: $testResult" -ForegroundColor White
} else {
    Write-Host "ERROR: Cleaned key still fails" -ForegroundColor Red
    Write-Host "Error: $testResult" -ForegroundColor Yellow
}

# Cleanup
Remove-Item $testKeyFile -Force
Write-Host ""

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Next Steps" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

Write-Host "The CLEANED key is now in your clipboard!" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Go to GitHub:" -ForegroundColor White
Write-Host "   https://github.com/saran625/ecommerce-fullstack/settings/secrets/actions" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. DELETE old EC2_SSH_KEY" -ForegroundColor White
Write-Host ""
Write-Host "3. Create NEW EC2_SSH_KEY:" -ForegroundColor White
Write-Host "   - Click 'New repository secret'" -ForegroundColor Gray
Write-Host "   - Name: EC2_SSH_KEY" -ForegroundColor Gray
Write-Host "   - Value: Press Ctrl+V (paste cleaned key)" -ForegroundColor Gray
Write-Host "   - Click 'Add secret'" -ForegroundColor Gray
Write-Host ""
Write-Host "4. The cleaned key has been saved to:" -ForegroundColor White
Write-Host "   $cleanedFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Update your workflow file with the new version" -ForegroundColor White
Write-Host ""

Write-Host "Done! Try pushing to GitHub again." -ForegroundColor Blue
Write-Host ""