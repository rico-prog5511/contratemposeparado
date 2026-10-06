# Publicar o contratempo no PythonAnywhere

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

## 3. Escolher o banco de dados

**Plano gratuito: SQLite (nada a fazer neste passo).** O MySQL do
PythonAnywhere só está disponível nos planos pagos. No plano grátis o site
usa SQLite: o banco é um único arquivo
(`~/contratemposeparado/contratempo/contratempo.sqlite3`), criado sozinho
no passo 5. Todas as funcionalidades continuam iguais, inclusive a busca
sem acentos. Pule para o passo 4.

<details>
<summary><strong>Plano pago: MySQL</strong></summary>

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

As tabelas são criadas pelo `migrate` do Django (passo 5), e não pelo
`banco/contratempo_db.sql`: o PythonAnywhere não dá permissão para o
`CREATE DATABASE` que o script usa. No `.env` do passo 5, use as linhas
indicadas para MySQL.
</details>

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

DB_ENGINE=sqlite

EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
BREVO_API_KEY=
```

> **E-mails no plano grátis:** o Gmail recusa o login vindo do servidor do
> PythonAnywhere (`SMTPServerDisconnected: Connection unexpectedly closed`),
> mesmo com a senha de app certa. Use o **Brevo** (brevo.com, grátis até
> 300 e-mails/dia):
>
> 1. Crie a conta no Brevo e confirme o seu Gmail como remetente
>    (*Senders, domains & IPs → Senders → Add a sender*).
> 2. Gere uma chave em *SMTP & API → API Keys → Generate a new API key*.
> 3. No `.env`: `EMAIL_HOST_USER=` o Gmail confirmado no Brevo e
>    `BREVO_API_KEY=` a chave. O `EMAIL_HOST_PASSWORD` deixa de ser usado.
> 4. Teste com `python manage.py testar_email seu@email.com` e dê **Reload**.

> **Só no plano pago com MySQL:** troque a linha `DB_ENGINE=sqlite` por:
>
> ```ini
> DB_ENGINE=mysql
> DB_NAME=SEUUSUARIO$contratempo
> DB_USER=SEUUSUARIO
> DB_PASSWORD=a-senha-do-passo-3
> DB_HOST=SEUUSUARIO.mysql.pythonanywhere-services.com
> DB_PORT=3306
> ```

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
4. Configure o **WSGI configuration file** pelo **Bash**, sem editar à mão.
   Colar o código no editor costuma deixar espaços no começo das linhas, e
   isso causa `IndentationError`. Rode o bloco abaixo **sem recuar
   nenhuma linha**, trocando `SEUUSUARIO` nas duas primeiras linhas:

```bash
cat > /var/www/enaldo_pythonanywhere_com_wsgi.py << 'EOF'
import os
import sys

caminho = "/home/enaldo/contratemposeparado/contratempo"
if caminho not in sys.path:
    sys.path.insert(0, caminho)

os.environ["DJANGO_SETTINGS_MODULE"] = "contratempo.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
EOF
python /var/www/enaldo_pythonanywhere_com_wsgi.py && echo "WSGI OK"
```

   O nome exato do arquivo aparece na aba **Web**, em *WSGI configuration
   file*. A última linha testa o arquivo e deve mostrar `WSGI OK`.

5. Em **Static files**, adicione duas linhas:

   | URL        | Directory                                                     |
   |------------|---------------------------------------------------------------|
   | `/static/` | `/home/SEUUSUARIO/contratemposeparado/contratempo/staticfiles` |
   | `/media/`  | `/home/SEUUSUARIO/contratemposeparado/contratempo/media`       |

6. Em **Security**, ative **Force HTTPS**.
7. Clique no botão verde **Reload** e abra
   `https://SEUUSUARIO.pythonanywhere.com`.

## 7. Publicar uma nova versão

1. **No seu computador:** abra o GitHub Desktop, escreva um resumo da
   alteração, clique em **Commit to main** e depois em **Push origin**.
2. **No PythonAnywhere (Bash):**

```bash
bash ~/contratemposeparado/atualizar.sh
```

O script baixa a versão nova (`git pull`), instala pacotes novos, aplica
as migrations, atualiza os arquivos estáticos e recarrega o site. Ele não
mexe no `.env`, nos dados nem nas fotos.

> A **primeira vez** que você rodar o script, o `atualizar.sh` ainda não
> existe no PythonAnywhere. Rode antes `cd ~/contratemposeparado && git pull`.
> O `git pull` pede o usuário do GitHub e o **token** no lugar da senha. Para
> não precisar digitá-lo toda vez, rode uma vez
> `git config --global credential.helper store`.

Sem o script, os passos manuais são:

```bash
workon contratempo
cd ~/contratemposeparado
git pull
pip install -r requirements.txt
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
| `IndentationError` no Error log | O arquivo WSGI tem espaços no começo das linhas. Recrie-o com o comando do passo 6.4. |
| "Bad Request (400)" | O endereço não está em `DJANGO_ALLOWED_HOSTS`. |
| Site sem estilo (sem CSS) | Faltou o `collectstatic` ou a linha `/static/` em **Static files**. Recarregue depois de corrigir. |
| Página com erro 500 logo depois de atualizar, ou CSS antigo | Com `DJANGO_DEBUG=0`, os CSS/JS ganham uma "impressão digital" no nome (`styles-retro.3f9a1c2b.css`) e o `collectstatic` precisa rodar a cada atualização. O `atualizar.sh` já faz isso; se atualizou à mão, rode `python manage.py collectstatic --noinput` e recarregue o site. |
| Fotos quebradas | Falta a linha `/media/` em **Static files**, ou a pasta `media` não foi enviada. |
| `Access denied for user` (só MySQL) | Confira `DB_USER`, `DB_PASSWORD` e `DB_HOST` no `.env`. |
| `no such table` (SQLite) | Faltou o `python manage.py migrate` do passo 5. |
| Fazer backup do banco e das fotos | No console Bash: `bash ~/contratemposeparado/backup.sh`. Gera `~/backups/contratempo-DATA.zip` (banco + pasta `media/`, sem o `.env`) e mantém os 5 mais recentes. Baixe o `.zip` pela aba **Files**. |
| E-mails não chegam | No plano gratuito o Gmail recusa o login vindo do servidor. Configure o **Brevo** (`BREVO_API_KEY`, ver passo 5). O site continua funcionando e o motivo aparece no **Server log**; `python manage.py testar_email seu@email.com` explica o erro. |
| Erro 403 "CSRF verification failed" | Acesse sempre pelo endereço com `https://` que está em `DJANGO_ALLOWED_HOSTS`. |
