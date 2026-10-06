"""
banco/criar_banco.py — usado pelo instalar.bat

Cria o banco do contratempo a partir de banco/contratempo_db.sql, usando
os dados de conexão do arquivo .env. Se o banco já existir, não mexe em
nada (o `manage.py migrate` que roda depois aplica o que faltar).
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "contratempo"))

try:
    import MySQLdb
    from MySQLdb.constants import CLIENT
except ImportError:
    sys.exit("ERRO: o pacote mysqlclient não está instalado (rode o instalar.bat).")

from contratempo import settings  # só lê o .env e as configurações; não inicia o Django

cfg = settings.DATABASES["default"]
if "sqlite" in cfg["ENGINE"]:
    print("Usando SQLite (sem servidor): o arquivo é criado pelo migrate.")
    sys.exit(0)
nome = cfg["NAME"]

try:
    con = MySQLdb.connect(
        host=cfg["HOST"], port=int(cfg["PORT"] or 3306), user=cfg["USER"],
        passwd=cfg["PASSWORD"], charset="utf8mb4", client_flag=CLIENT.MULTI_STATEMENTS,
    )
except MySQLdb.OperationalError as erro:
    codigo = erro.args[0]
    if codigo == 1045:
        sys.exit(f"ERRO: o MySQL recusou o usuário '{cfg['USER']}' com essa senha. Corrija DB_PASSWORD no arquivo .env.")
    if codigo in (2002, 2003):
        sys.exit(f"ERRO: não há MySQL rodando em {cfg['HOST']}:{cfg['PORT']}. Instale/inicie o MySQL Server 8 e rode de novo.")
    sys.exit(f"ERRO ao conectar no MySQL: {erro}")

cur = con.cursor()
cur.execute("SHOW DATABASES LIKE %s", (nome,))
if cur.fetchone():
    print(f"Banco '{nome}' já existe — mantido como está.")
    sys.exit(0)

script = (RAIZ / "banco" / "contratempo_db.sql").read_text(encoding="utf-8")
script = script.replace("`contratempo_db`", f"`{nome}`")
cur.execute(script)
while cur.nextset() is not None:  # executa todos os comandos do arquivo
    pass
con.commit()
con.close()
print(f"Banco '{nome}' criado a partir de banco/contratempo_db.sql.")
