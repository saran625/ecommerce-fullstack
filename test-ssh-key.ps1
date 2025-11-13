# Test SSH Key Script - Fixed Version
# This verifies your SSH key will work with GitHub Actions
# Save as: test-ssh-key.ps1
# Run: .\test-ssh-key.ps1

$pemFile = "C:\Users\Admin\OneDrive\Desktop\ecommerce-fullstack\newkeypair.pem"
$ec2Host = "3.84.242.4"
$ec2User = "ubuntu"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  SSH Key Test for GitHub Actions" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Test 1: Check file exists
Write-Host "TEST 1 - Checking .pem file..." -ForegroundColor Cyan
if (Test-Path $pemFile) {
    Write-Host "PASS - File exists: $pemFile" -ForegroundColor Green
} else {
    Write-Host "FAIL - File not found!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: Check file size
Write-Host "TEST 2 - Checking file size..." -ForegroundColor Cyan
$fileSize = (Get-Item $pemFile).Length
Write-Host "File size: $fileSize bytes" -ForegroundColor White
if ($fileSize -gt 1000 -and $fileSize -lt 5000) {
    Write-Host "PASS - File size looks correct" -ForegroundColor Green
} else {
    Write-Host "WARN - File size seems unusual" -ForegroundColor Yellow
}
Write-Host ""

# Test 3: Verify key format
Write-Host "TEST 3 - Verifying key format..." -ForegroundColor Cyan
$keyContent = Get-Content $pemFile -Raw
if ($keyContent -match "-----BEGIN.*PRIVATE KEY-----" -and $keyContent -match "-----END.*PRIVATE KEY-----") {
    Write-Host "PASS - Key has proper BEGIN/END markers" -ForegroundColor Green
    if ($keyContent -match "BEGIN RSA PRIVATE KEY") {
        Write-Host "  Type: RSA Private Key" -ForegroundColor Gray
    } elseif ($keyContent -match "BEGIN OPENSSH PRIVATE KEY") {
        Write-Host "  Type: OpenSSH Private Key" -ForegroundColor Gray
    }
} else {
    Write-Host "FAIL - Key format invalid!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 4: Check line count
Write-Host "TEST 4 - Checking line count..." -ForegroundColor Cyan
$lines = (Get-Content $pemFile).Count
Write-Host "Total lines: $lines" -ForegroundColor White
if ($lines -ge 25) {
    Write-Host "PASS - Line count looks good" -ForegroundColor Green
} else {
    Write-Host "WARN - Unusually few lines" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: Test SSH connection
Write-Host "TEST 5 - Testing SSH connection to EC2..." -ForegroundColor Cyan
Write-Host "Running: ssh -i $pemFile $ec2User@$ec2Host whoami" -ForegroundColor Gray

try {
    $sshTest = ssh -i $pemFile -o StrictHostKeyChecking=no $ec2User@$ec2Host "whoami" 2>&1
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "FAIL - SSH command error: $_" -ForegroundColor Red
    exit 1
}

if ($exitCode -eq 0) {
    Write-Host "PASS - SSH connection successful!" -ForegroundColor Green
    Write-Host "  EC2 user: $sshTest" -ForegroundColor Gray
} else {
    Write-Host "FAIL - SSH connection failed!" -ForegroundColor Red
    Write-Host "Error: $sshTest" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "  1. Wrong EC2 username (try 'ec2-user' instead of 'ubuntu')" -ForegroundColor White
    Write-Host "  2. Security group not allowing SSH from your IP" -ForegroundColor White
    Write-Host "  3. Wrong .pem file for this EC2 instance" -ForegroundColor White
    exit 1
}
Write-Host ""

# Test 6: Check EC2 Docker setup
Write-Host "TEST 6 - Checking Docker on EC2..." -ForegroundColor Cyan
try {
    $dockerTest = ssh -i $pemFile $ec2User@$ec2Host "docker --version" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PASS - Docker is installed: $dockerTest" -ForegroundColor Green
    } else {
        Write-Host "WARN - Docker not found or not accessible" -ForegroundColor Yellow
    }
} catch {
    Write-Host "WARN - Could not check Docker" -ForegroundColor Yellow
}
Write-Host ""

# Test 7: Check project directory
Write-Host "TEST 7 - Checking project directory on EC2..." -ForegroundColor Cyan
try {
    $dirTest = ssh -i $pemFile $ec2User@$ec2Host "ls -la ~/ecommerce-fullstack" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PASS - Project directory exists" -ForegroundColor Green
    } else {
        Write-Host "WARN - Project directory not found (will be created on first deploy)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "WARN - Could not check directory" -ForegroundColor Yellow
}
Write-Host ""

# Test 8: Prepare key for GitHub
Write-Host "TEST 8 - Preparing key for GitHub Secret..." -ForegroundColor Cyan
$keyForGitHub = Get-Content $pemFile -Raw
$keyForGitHub | Set-Clipboard
Write-Host "PASS - Key copied to clipboard!" -ForegroundColor Green
Write-Host ""

# Display summary
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Test Summary" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

Write-Host "Key file: $pemFile" -ForegroundColor White
Write-Host "EC2 Host: $ec2Host" -ForegroundColor White
Write-Host "EC2 User: $ec2User" -ForegroundColor White
Write-Host ""

Write-Host "SUCCESS - SSH key is VALID and WORKING!" -ForegroundColor Green
Write-Host "SUCCESS - Key is copied to clipboard" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Next Steps" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

Write-Host "1. Go to GitHub Secrets:" -ForegroundColor Yellow
Write-Host "   https://github.com/saran625/ecommerce-fullstack/settings/secrets/actions" -ForegroundColor Cyan
Write-Host ""

Write-Host "2. DELETE the old EC2_SSH_KEY secret" -ForegroundColor Yellow
Write-Host ""

Write-Host "3. Create NEW secret:" -ForegroundColor Yellow
Write-Host "   Name: EC2_SSH_KEY" -ForegroundColor White
Write-Host "   Value: Press Ctrl+V (paste from clipboard)" -ForegroundColor White
Write-Host ""

Write-Host "4. Verify these secrets exist:" -ForegroundColor Yellow
Write-Host "   DOCKER_USERNAME = your dockerhub username" -ForegroundColor White
Write-Host "   DOCKER_PASSWORD = your dockerhub password" -ForegroundColor White
Write-Host "   EC2_HOST = 3.84.242.4" -ForegroundColor White
Write-Host "   EC2_USER = ubuntu" -ForegroundColor White
Write-Host ""

Write-Host "5. Update your workflow file to: .github/workflows/deploy.yml" -ForegroundColor Yellow
Write-Host ""

Write-Host "6. Push and test:" -ForegroundColor Yellow
Write-Host "   git add ." -ForegroundColor Cyan
Write-Host "   git commit -m 'Fix: Improve SSH handling'" -ForegroundColor Cyan
Write-Host "   git push origin main" -ForegroundColor Cyan
Write-Host ""

Write-Host "SUCCESS - Your SSH key is ready for GitHub Actions!" -ForegroundColor Blue
Write-Host ""