#!/bin/bash
# atualizar.sh — atualiza o site no PythonAnywhere com a última versão do GitHub.
#
# Uso, no console Bash do PythonAnywhere:
#     bash ~/contratemposeparado/atualizar.sh
#
# Não mexe no .env, no banco de dados (só aplica migrations novas) nem nas
# fotos enviadas pelos usuários.

set -e  # para no primeiro erro

cd ~/contratemposeparado
source ~/.virtualenvs/contratempo/bin/activate

echo "==> Baixando a versão nova do GitHub"
git pull

echo "==> Instalando pacotes novos (se houver)"
pip install --quiet -r requirements.txt

cd contratempo

echo "==> Atualizando o banco de dados"
python manage.py migrate --noinput

echo "==> Atualizando CSS, JavaScript e imagens do site"
python manage.py collectstatic --noinput

echo "==> Reiniciando o site"
# No PythonAnywhere, "tocar" o arquivo WSGI recarrega o site (= botão Reload).
touch "/var/www/${USER}_pythonanywhere_com_wsgi.py"

echo ""
echo "Pronto! Site atualizado: https://${USER}.pythonanywhere.com"
