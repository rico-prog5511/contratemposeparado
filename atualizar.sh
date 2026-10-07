#!/bin/bash

set -e

cd ~/contratemposeparado
source ~/.virtualenvs/contratempo/bin/activate

echo "==> Baixando a versão nova do GitHub"
git pull

echo "==> Instalando pacotes novos (se houver)"
pip install --quiet -r requirements.txt

cd contratempo

echo "==> Atualizando o banco de dados"
python manage.py migrate --noinput

echo "==> Gerando as versões leves da foto do banner (se houver foto nova)"
python manage.py otimizar_banner

echo "==> Convertendo fotos antigas de produtos e de perfil (se houver)"
python manage.py otimizar_fotos

echo "==> Atualizando CSS, JavaScript e imagens do site"
python manage.py collectstatic --noinput

echo "==> Reiniciando o site"
touch "/var/www/${USER}_pythonanywhere_com_wsgi.py"

echo ""
echo "Pronto! Site atualizado: https://${USER}.pythonanywhere.com"
