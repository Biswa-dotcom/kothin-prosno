# Check if command exists
function Command-Exists {
    param([string]$command)
    return (Get-Command $command -ErrorAction SilentlyContinue) -ne $null
}

Write-Host "`n[1/4] Checking if Ollama is installed..." -ForegroundColor Cyan
if (-not (Command-Exists "ollama")) {
    Write-Host "[!] Ollama is not installed. Downloading..." -ForegroundColor Yellow
    Start-Process "https://ollama.com/download/OllamaSetup.exe"
    Write-Host "[i] Please install Ollama manually from the installer, then re-run this script." -ForegroundColor Magenta
    exit
} else {
    Write-Host "[✓] Ollama is installed." -ForegroundColor Green
}

Write-Host "`n[2/4] Checking if 'llama2' model is pulled..." -ForegroundColor Cyan
$models = & ollama list
if ($models -notmatch "llama2") {
    Write-Host "[+] Pulling llama2 model..." -ForegroundColor Yellow
    & ollama pull llama2
} else {
    Write-Host "[✓] llama2 model is already available." -ForegroundColor Green
}

Write-Host "`n[3/4] Installing Python requirements..." -ForegroundColor Cyan
if (Test-Path "requirements.txt") {
    & python -m pip install -r requirements.txt
    Write-Host "[✓] Dependencies installed." -ForegroundColor Green
} else {
    Write-Host "[✗] requirements.txt not found!" -ForegroundColor Red
    exit
}

Write-Host "`n[4/4] Running main.py..." -ForegroundColor Cyan
# Option 1: Directly run main.py (if FastAPI runs via __main__)
# & python main.py

# Option 2: Run with uvicorn (recommended)
& python -m uvicorn main:app --reload
