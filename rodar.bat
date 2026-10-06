@echo off
rem Abre o contratempo em http://127.0.0.1:8000 (feche esta janela para parar).
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
rem Gera as versoes leves da foto do banner, se ela foi trocada.
venv\Scripts\python.exe contratempo\manage.py otimizar_banner
rem Converte fotos antigas de produtos/perfil para o formato leve (so as que faltarem).
venv\Scripts\python.exe contratempo\manage.py otimizar_fotos
start "" http://127.0.0.1:8000/
venv\Scripts\python.exe contratempo\manage.py runserver
pause
