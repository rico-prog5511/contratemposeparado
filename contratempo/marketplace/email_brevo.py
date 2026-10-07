import base64
import json
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

URL_API = "https://api.brevo.com/v3/smtp/email"


class BrevoErro(Exception):

    def __init__(self, status, codigo, mensagem):
        self.status, self.codigo, self.mensagem = status, codigo, mensagem
        super().__init__(f"Brevo respondeu {status} ({codigo}): {mensagem}")


def _contato(endereco):
    nome, email = parseaddr(endereco)
    return {"email": email, "name": nome} if nome else {"email": email}


def _contatos(enderecos):
    return [_contato(endereco) for endereco in enderecos]


def montar_payload(mensagem):
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
    for anexo in mensagem.attachments:
        if isinstance(anexo, tuple):
            nome, conteudo = anexo[0], anexo[1]
            dados = conteudo.encode() if isinstance(conteudo, str) else conteudo
            anexos.append({"name": nome or "anexo", "content": base64.b64encode(dados).decode()})
    if anexos:
        payload["attachment"] = anexos
    return payload


class BrevoEmailBackend(BaseEmailBackend):

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
