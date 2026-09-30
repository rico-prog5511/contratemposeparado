@echo off
rem Abre o Contratempo em http://127.0.0.1:8000 (feche esta janela para parar).
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Rode o instalar.bat primeiro.
    pause
    exit /b 1
)
rem Aplica alteracoes novas do banco (se houver) antes de abrir o site.
venv\Scripts\python.exe contratempo\manage.py migrate --noinput
if errorlevel 1 (
    echo.
    echo Nao foi possivel atualizar o banco. Veja a mensagem acima.
    pause
    exit /b 1
)
start "" http://127.0.0.1:8000/
venv\Scripts\python.exe contratempo\manage.py runserver
pause
