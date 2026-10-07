$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Falha($texto) { Write-Host "`nERRO: $texto" -ForegroundColor Red; exit 1 }

Passo "Procurando o Python"
$python = $null
foreach ($candidato in @("py -3", "python")) {
    try {
        $versao = & ([scriptblock]::Create("$candidato -c `"import sys; print('%d.%d' % sys.version_info[:2])`"")) 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$versao -ge [version]"3.10") { $python = $candidato; break }
    } catch { }
}
if (-not $python) { Falha "Python 3.10 ou mais novo não encontrado. Instale em python.org marcando 'Add python.exe to PATH'." }
Write-Host "Python $versao ($python)"

$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -c "import sys" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Passo "A pasta venv veio de outra máquina e não funciona aqui — recriando"
        Remove-Item -Recurse -Force (Join-Path $PSScriptRoot "venv")
    }
}
if (-not (Test-Path $venvPython)) {
    Passo "Criando o ambiente virtual (venv)"
    & ([scriptblock]::Create("$python -m venv venv"))
    if (-not (Test-Path $venvPython)) { Falha "não foi possível criar a venv." }
}

Passo "Instalando os pacotes (Django, mysqlclient, Pillow)"
& $venvPython -m pip install --upgrade pip --quiet --disable-pip-version-check
& $venvPython -m pip install -r requirements.txt --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Falha "falha ao instalar os pacotes do requirements.txt." }

if (-not (Test-Path ".env")) {
    Passo "Criando o arquivo .env (configuração desta máquina)"
    $conteudo = Get-Content ".env.exemplo" -Raw -Encoding UTF8
    $modo = Read-Host "Esta máquina tem MySQL Server instalado? (s = usar MySQL / n = usar SQLite, sem servidor)"
    if ($modo -match "^[sS]") {
        $senha = Read-Host "Senha do usuário root do MySQL nesta máquina"
        $conteudo = $conteudo -replace "(?m)^DB_PASSWORD=.*$", "DB_PASSWORD=$senha"
    } else {
        $conteudo = $conteudo -replace "(?m)^DB_ENGINE=.*$", "DB_ENGINE=sqlite"
    }
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot ".env"), $conteudo, (New-Object Text.UTF8Encoding $false))
    Write-Host "Criado. Para outro usuário/porta do MySQL ou para o e-mail, edite o .env."
} else {
    Write-Host "`nArquivo .env já existe — mantido."
}

Passo "Preparando o banco MySQL"
& $venvPython banco\criar_banco.py
if ($LASTEXITCODE -ne 0) { Falha "corrija o problema acima e rode o instalar.bat de novo." }

$sqlite = (Get-Content ".env" -Encoding UTF8) -match "^\s*DB_ENGINE\s*=\s*sqlite"
$arquivoSqlite = "contratempo\contratempo.sqlite3"
$sqliteNovo = $sqlite -and -not (Test-Path $arquivoSqlite)

Passo "Aplicando as migrations do Django"
& $venvPython contratempo\manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { Falha "o migrate falhou (veja a mensagem acima)." }

if ($sqliteNovo -and (Test-Path "banco\dados.json")) {
    Passo "Carregando os dados exportados (banco\dados.json)"
    & $venvPython -X utf8 contratempo\manage.py loaddata banco\dados.json
    if ($LASTEXITCODE -ne 0) { Falha "não foi possível carregar banco\dados.json." }
}

$resposta = Read-Host "`nCriar um usuário administrador para o /admin/ agora? (s/n)"
if ($resposta -match "^[sS]") {
    & $venvPython contratempo\manage.py createsuperuser
}

Write-Host "`nPronto! Para abrir o site, dê dois cliques em rodar.bat" -ForegroundColor Green
Write-Host "(ou rode: venv\Scripts\python contratempo\manage.py runserver)"
