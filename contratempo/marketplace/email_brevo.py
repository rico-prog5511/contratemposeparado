"""
marketplace/email_brevo.py

Envio de e-mails pela API do Brevo (brevo.com), em vez do Gmail.

Por quê: no plano grátis do PythonAnywhere o Gmail recusa o login vindo
do servidor (o mesmo usuário e senha funcionam no PC). O Brevo é chamado
por HTTPS — api.brevo.com está na lista de sites liberados do plano grátis
— e envia até 300 e-mails/dia de graça.

Como ligar: coloque BREVO_API_KEY no .env (ver .env.exemplo). O remetente
continua sendo DEFAULT_FROM_EMAIL ("Contratempo <EMAIL_HOST_USER>"), e esse
endereço precisa estar confirmado no Brevo (Senders, domains & IPs).
Sem a chave, o site segue usando o Gmail/terminal como antes.

Não usa biblioteca nova: só urllib (o PythonAnywhere já configura o proxy
nas variáveis de ambiente, que o urllib respeita sozinho).
"""

import base64
import json
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

URL_API = "https://api.brevo.com/v3/smtp/email"


class BrevoErro(Exception):
    """Resposta de erro da API do Brevo (status HTTP + mensagem dele)."""

    def __init__(self, status, codigo, mensagem):
        self.status, self.codigo, self.mensagem = status, codigo, mensagem
        super().__init__(f"Brevo respondeu {status} ({codigo}): {mensagem}")


def _contato(endereco):
    nome, email = parseaddr(endereco)
    return {"email": email, "name": nome} if nome else {"email": email}


def _contatos(enderecos):
    return [_contato(endereco) for endereco in enderecos]


def montar_payload(mensagem):
    """EmailMessage/EmailMultiAlternatives do Django -> JSON da API do Brevo."""
    payload = {
        "sender": _contato(mensagem.from_email or settings.DEFAULT_FROM_EMAIL),
        "to": _contatos(mensagem.to),
        "subject": mensagem.subject,
    }
    if mensagem.cc:
        payload["cc"] = _contatos(mensagem.cc)
    if mensagem.bcc:
        payload["bcc"] = _contatos(mensagem.bcc)
    if mensagem.reply_to:
        payload["replyTo"] = _contato(mensagem.reply_to[0])

    if getattr(mensagem, "content_subtype", "plain") == "html":
        payload["htmlContent"] = mensagem.body
    else:
        payload["textContent"] = mensagem.body
    for conteudo, tipo in getattr(mensagem, "alternatives", []) or []:
        if tipo == "text/html":
            payload["htmlContent"] = conteudo

    anexos = []
    for anexo in mensagem.attachments:  # (nome, conteúdo, tipo); o site hoje não manda anexos
        if isinstance(anexo, tuple):
            nome, conteudo = anexo[0], anexo[1]
            dados = conteudo.encode() if isinstance(conteudo, str) else conteudo
            anexos.append({"name": nome or "anexo", "content": base64.b64encode(dados).decode()})
    if anexos:
        payload["attachment"] = anexos
    return payload


class BrevoEmailBackend(BaseEmailBackend):
    """EMAIL_BACKEND que envia cada mensagem por um POST na API do Brevo."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.chave = getattr(settings, "BREVO_API_KEY", "")
        self.timeout = getattr(settings, "EMAIL_TIMEOUT", None) or 20

    def _enviar(self, mensagem):
        if not mensagem.recipients():
            return False
        pedido = urllib.request.Request(
            URL_API,
            data=json.dumps(montar_payload(mensagem)).encode("utf-8"),
            headers={"api-key": self.chave, "content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                return 200 <= resposta.status < 300
        except urllib.error.HTTPError as erro:
            try:
                corpo = json.loads(erro.read().decode("utf-8") or "{}")
            except ValueError:
                corpo = {}
            raise BrevoErro(erro.code, corpo.get("code", ""), corpo.get("message", erro.reason)) from None

    def send_messages(self, email_messages):
        enviados = 0
        for mensagem in email_messages:
            try:
                if self._enviar(mensagem):
                    enviados += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return enviados
