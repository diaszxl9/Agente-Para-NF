# Cria (ou repara) o ambiente virtual do backend e instala TODAS as dependências.
# Uso, a partir da raiz do projeto:
#   powershell -ExecutionPolicy Bypass -File backend\setup.ps1
# Pode ser executado quantas vezes for preciso: um .venv incompleto é recriado automaticamente.

$ErrorActionPreference = "Stop"

$backend = $PSScriptRoot
$venv = Join-Path $backend ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"

function Invoke-Checked {
    param([string]$Description, [string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao $Description (código $LASTEXITCODE)."
    }
}

# Executa um comando só para saber se ele funciona. No Windows PowerShell 5.1, o stderr de um executável
# nativo vira erro terminante com $ErrorActionPreference = "Stop"; por isso a sondagem roda com "Continue".
function Test-Exe {
    param([string]$Exe, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Exe @Arguments 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Test-Pip {
    if (-not (Test-Path $venvPython)) { return $false }
    return (Test-Exe $venvPython @("-m", "pip", "--version"))
}

# 1) Localiza um Python 3.11+
$python = $null
foreach ($candidate in @("python", "py")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    $pyArgs = if ($candidate -eq "py") { @("-3") } else { @() }
    $versionCheck = "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if (Test-Exe $cmd.Source ($pyArgs + @("-c", $versionCheck))) {
        $python = @{ Exe = $cmd.Source; Args = $pyArgs }
        break
    }
}
if (-not $python) {
    throw "Python 3.11 ou superior não encontrado. Instale em https://www.python.org/downloads/ e marque 'Add to PATH'."
}

# 2) Cria o venv; se já existir mas estiver incompleto (sem pip), recria do zero.
# Antivírus, indexador do Windows ou o VS Code podem segurar o python.exe recém-copiado por alguns segundos
# ("Acesso negado"), o que interrompe o "python -m venv" no meio e deixa um .venv sem pip. Por isso há tentativas.
if (-not (Test-Pip)) {
    $criado = $false
    foreach ($tentativa in 1..3) {
        if (Test-Path $venv) {
            Write-Host "Removendo ambiente virtual incompleto (tentativa $tentativa)..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $venv -ErrorAction SilentlyContinue
        }
        Write-Host "Criando ambiente virtual (tentativa $tentativa)..."
        & $python.Exe @($python.Args + @("-m", "venv", $venv))
        if (($LASTEXITCODE -eq 0) -and (Test-Pip)) {
            $criado = $true
            break
        }
        Start-Sleep -Seconds 3
    }
    if (-not $criado) {
        throw ("Não foi possível criar o ambiente virtual em '$venv'. Feche terminais/editores que usam esse .venv, " +
            "apague a pasta manualmente e rode o script de novo. Se persistir, exclua a pasta do projeto do antivírus.")
    }
}

# 3) Instala as dependências (é aqui que os pacotes realmente são instalados)
Write-Host "Instalando dependências..."
Invoke-Checked "atualizar o pip" $venvPython @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked "instalar o requirements.txt" $venvPython @("-m", "pip", "install", "-r", (Join-Path $backend "requirements.txt"))

# 4) Verifica: dependências consistentes e aplicação importável
Invoke-Checked "verificar as dependências (pip check)" $venvPython @("-m", "pip", "check")
Push-Location $backend
try {
    Invoke-Checked "importar a aplicação" $venvPython @(
        "-c",
        "import app.main, multipart, pytest, httpx; print('Aplicação importada com sucesso.')"
    )
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Backend pronto. Para iniciar:" -ForegroundColor Green
Write-Host "  cd backend"
Write-Host "  .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
