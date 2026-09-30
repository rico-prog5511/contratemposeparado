# Publicar o Contratempo no PythonAnywhere

Guia passo a passo para colocar o site no ar, de graça, em
`https://SEUUSUARIO.pythonanywhere.com`.

> Em todo o guia, troque **`SEUUSUARIO`** pelo seu nome de usuário do
> PythonAnywhere. Ele vira o endereço do site.
>
> As telas e os limites do plano gratuito mudam de vez em quando. Se algum
> botão tiver outro nome, procure a opção equivalente.

---

## 1. Criar a conta

1. Acesse [pythonanywhere.com](https://www.pythonanywhere.com) e crie uma
   conta **Beginner** (gratuita).
2. Confirme o e-mail.

## 2. Enviar o projeto

Escolha **uma** das opções.

**Opção A — GitHub (recomendada).** Com o projeto num repositório, abra
**Consoles > Bash** e rode:

```bash
git clone https://github.com/SEU_GITHUB/contratemposeparado.git
```

O `.gitignore` já impede que a `venv`, o `.env` e as fotos sejam enviados.
As fotos você envia no passo 5.

**Opção B — arquivo .zip.**

1. No seu computador, compacte a pasta `contratemposeparado` **sem** a
   pasta `venv` e sem o arquivo `.env`.
2. Na aba **Files**, clique em *Upload a file* e envie o `.zip`.
3. Em **Consoles > Bash**, rode `unzip contratemposeparado.zip`.

## 3. Criar o banco MySQL

1. Aba **Databases**: defina uma senha para o MySQL e anote-a.
2. Em *Create a database*, digite `contratempo` e confirme. O nome
   completo do banco será `SEUUSUARIO$contratempo`.
3. Anote o **Database host**, que aparece no topo da página:
   `SEUUSUARIO.mysql.pythonanywhere-services.com`.
4. Clique no banco para abrir o console do MySQL e rode o comando abaixo,
   para acentos e emojis funcionarem:

```sql
ALTER DATABASE `SEUUSUARIO$contratempo` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

> No PythonAnywhere as tabelas são criadas pelo `migrate` do Django (passo
> 5), e não pelo `banco/contratempo_db.sql`. A conta gratuita não tem
> permissão para o `CREATE DATABASE` que o script usa.

## 4. Instalar os pacotes

No **Bash**:

```bash
mkvirtualenv --python=python3.13 contratempo
cd ~/contratemposeparado
pip install -r requirements.txt
```

> Se o Python 3.13 não estiver disponível, use a versão mais nova da lista
> (3.10 ou mais nova). Depois de fechar o console, entre de novo no
> ambiente com `workon contratempo`.

## 5. Configurar o `.env`

Gere uma chave secreta e copie o resultado:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g()+g())"
```

Crie o arquivo com `nano ~/contratemposeparado/.env`. Cole o conteúdo
abaixo, preenchendo os valores, e salve com `Ctrl+O`, `Enter` e `Ctrl+X`:

```ini
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=SEUUSUARIO.pythonanywhere.com
DJANGO_SECRET_KEY=cole-a-chave-gerada-aqui

DB_ENGINE=mysql
DB_NAME=SEUUSUARIO$contratempo
DB_USER=SEUUSUARIO
DB_PASSWORD=a-senha-do-passo-3
DB_HOST=SEUUSUARIO.mysql.pythonanywhere-services.com
DB_PORT=3306

EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

Depois crie as tabelas, copie os arquivos estáticos e crie o administrador:

```bash
cd ~/contratemposeparado/contratempo
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

**Opcional: levar os dados do seu computador** (usuários, anúncios e
pedidos). Antes, gere o `banco/dados.json` no seu computador com o comando
do README. Depois envie a pasta `contratempo/media` (as fotos) pela aba
**Files** para `~/contratemposeparado/contratempo/media` e rode:

```bash
python -X utf8 manage.py loaddata ../banco/dados.json
```

## 6. Criar o site

Na aba **Web**:

1. **Add a new web app**, escolha **Manual configuration** (não use a opção
   "Django") e a **mesma versão do Python** do passo 4.
2. Em **Virtualenv**, informe `/home/SEUUSUARIO/.virtualenvs/contratempo`.
3. Em **Code**, informe:
   - Source code: `/home/SEUUSUARIO/contratemposeparado/contratempo`
   - Working directory: `/home/SEUUSUARIO/contratemposeparado/contratempo`
4. Clique no link do **WSGI configuration file**, **apague tudo** e cole:

   ```python
   import os
   import sys

   caminho = "/home/SEUUSUARIO/contratemposeparado/contratempo"
   if caminho not in sys.path:
       sys.path.insert(0, caminho)

   os.environ["DJANGO_SETTINGS_MODULE"] = "contratempo.settings"

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

5. Em **Static files**, adicione duas linhas:

   | URL        | Directory                                                     |
   |------------|---------------------------------------------------------------|
   | `/static/` | `/home/SEUUSUARIO/contratemposeparado/contratempo/staticfiles` |
   | `/media/`  | `/home/SEUUSUARIO/contratemposeparado/contratempo/media`       |

6. Em **Security**, ative **Force HTTPS**.
7. Clique no botão verde **Reload** e abra
   `https://SEUUSUARIO.pythonanywhere.com`.

## 7. Publicar uma nova versão

Depois de alterar o projeto no seu computador:

```bash
workon contratempo
cd ~/contratemposeparado
git pull                                  # ou envie os arquivos de novo pela aba Files
cd contratempo
python manage.py migrate
python manage.py collectstatic --noinput
```

Depois, clique em **Reload** na aba **Web**.

## Manter o site no ar

Na conta gratuita o site é desligado se ninguém renová-lo. Entre no
PythonAnywhere pelo menos a cada 3 meses e clique em **Run until 3 months
from today**, na aba **Web**.

## Problemas comuns

| Sintoma | Causa e solução |
|---|---|
| "Something went wrong" / erro 500 | Veja o **Error log** na aba **Web**. As causas mais comuns são um erro no `.env` ou esquecer o `migrate`. |
| `ImproperlyConfigured: defina DJANGO_SECRET_KEY` | Falta `DJANGO_SECRET_KEY` no `.env`. |
| "Bad Request (400)" | O endereço não está em `DJANGO_ALLOWED_HOSTS`. |
| Site sem estilo (sem CSS) | Faltou o `collectstatic` ou a linha `/static/` em **Static files**. Recarregue depois de corrigir. |
| Fotos quebradas | Falta a linha `/media/` em **Static files**, ou a pasta `media` não foi enviada. |
| `Access denied for user` | Confira `DB_USER`, `DB_PASSWORD` e `DB_HOST` no `.env`. |
| E-mails não chegam | O plano gratuito limita o acesso à internet, e o envio pelo Gmail pode ser bloqueado. O site continua funcionando e o motivo aparece no **Server log**. |
| Erro 403 "CSRF verification failed" | Acesse sempre pelo endereço com `https://` que está em `DJANGO_ALLOWED_HOSTS`. |
