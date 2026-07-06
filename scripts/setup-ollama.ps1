param(
  [string]$Model = "llama3.1:8b",
  [switch]$Install
)

$ErrorActionPreference = "Stop"

function Test-CommandExists {
  param([string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "ollama")) {
  Write-Host "Ollama is not available in PATH."

  if (-not $Install) {
    Write-Host "Install manually from https://ollama.com/download or rerun:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\setup-ollama.ps1 -Install"
    exit 1
  }

  if (-not (Test-CommandExists "winget")) {
    throw "winget is not available. Install Ollama manually from https://ollama.com/download"
  }

  Write-Host "Installing Ollama via winget..."
  Write-Host "If winget hangs for a long time, cancel it and install manually from https://ollama.com/download"
  winget install --id Ollama.Ollama -e --silent --disable-interactivity --accept-package-agreements --accept-source-agreements

  if (-not (Test-CommandExists "ollama")) {
    Write-Host "Ollama was installed, but this terminal cannot see it yet."
    Write-Host "Open a new terminal and run this script again."
    Write-Host "If winget did not finish, install manually from https://ollama.com/download"
    exit 1
  }
}

ollama --version

Write-Host "Pulling model $Model..."
ollama pull $Model

Write-Host "Installed Ollama models:"
ollama list

Write-Host "Done. Project health check:"
python -m n1_project.worker --doctor
