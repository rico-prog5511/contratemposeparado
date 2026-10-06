#!/bin/bash
# backup.sh — guarda uma cópia do banco de dados e das fotos do site.
#
# Uso, no console Bash do PythonAnywhere:
#     bash ~/contratemposeparado/backup.sh
#
# Gera ~/backups/contratempo-AAAA-MM-DD-HHMM.zip com:
#   - banco.sqlite3 (ou banco.sql, se o .env usar MySQL)
#   - media/ (fotos dos produtos e dos perfis)
# Mantém só os 5 backups mais recentes. Baixe o .zip pela aba Files:
# uma cópia que fica só no servidor não protege contra problemas na conta.
#
# O .env NÃO entra no backup (tem senhas). Guarde uma cópia dele à parte.
#
# Para restaurar: descompacte o .zip e copie banco.sqlite3 para
# ~/contratemposeparado/contratempo/contratempo.sqlite3 e a pasta media/
# para ~/contratemposeparado/contratempo/media/; depois clique em Reload.

set -e  # para no primeiro erro

PROJETO=~/contratemposeparado
DESTINO=~/backups
NOME="contratempo-$(date +%Y-%m-%d-%H%M)"
TEMP="$DESTINO/$NOME"

# Lê uma variável do .env (vazio se não existir).
ler_env() {
    grep -E "^$1=" "$PROJETO/.env" 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']$//"
}

mkdir -p "$TEMP"
cd "$PROJETO/contratempo"
source ~/.virtualenvs/contratempo/bin/activate

if [ "$(ler_env DB_ENGINE | tr 'A-Z' 'a-z')" = "mysql" ]; then
    echo "==> Copiando o banco MySQL"
    MYSQL_PWD="$(ler_env DB_PASSWORD)" mysqldump --no-tablespaces \
        -h "$(ler_env DB_HOST)" -u "$(ler_env DB_USER)" "$(ler_env DB_NAME)" > "$TEMP/banco.sql"
else
    echo "==> Copiando o banco SQLite"
    if [ ! -f contratempo.sqlite3 ]; then
        echo "ERRO: não achei contratempo/contratempo.sqlite3"
        exit 1
    fi
    # A cópia pelo próprio SQLite fica íntegra mesmo com o site no ar.
    python -c "import sqlite3, sys; o = sqlite3.connect('contratempo.sqlite3'); d = sqlite3.connect(sys.argv[1]); o.backup(d); d.close(); o.close()" "$TEMP/banco.sqlite3"
fi

echo "==> Juntando banco e fotos em $NOME.zip"
if [ -d media ]; then
    cp -r media "$TEMP/media"
fi
(cd "$DESTINO" && zip -qr "$NOME.zip" "$NOME")
rm -rf "$TEMP"

echo "==> Apagando backups antigos (ficam os 5 mais recentes)"
ls -1t "$DESTINO"/contratempo-*.zip | tail -n +6 | xargs -r rm --

echo ""
echo "Pronto! Backup salvo em $DESTINO/$NOME.zip ($(du -h "$DESTINO/$NOME.zip" | cut -f1))"
echo "Baixe pela aba Files > backups para guardar no seu computador."
