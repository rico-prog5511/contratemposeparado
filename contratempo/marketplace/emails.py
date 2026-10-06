"""
marketplace/emails.py

Envio de todos os e-mails do contratempo e o token de confirmação de
cadastro. Os templates ficam em templates/emails/ e estendem
emails/base.html (HTML com estilos inline, que é o que os clientes de
e-mail entendem). A versão em texto puro é gerada automaticamente.

Uma falha de envio NUNCA derruba a ação do usuário (compra, pergunta,
mudança de status): o erro vai para o log e a função devolve False.
"""

import logging
import smtplib
import socket
import ssl

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


class ConfirmacaoEmailTokenGenerator(PasswordResetTokenGenerator):
    """
    Token do link de confirmação de cadastro. Inclui `email_confirmado`
    no hash, então o link deixa de valer assim que for usado. Expira em
    settings.PASSWORD_RESET_TIMEOUT.
    """

    key_salt = "marketplace.emails.ConfirmacaoEmailTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_confirmado}{timestamp}"


token_confirmacao = ConfirmacaoEmailTokenGenerator()


def enviar_email(request, assunto, template, contexto, para):
    """Renderiza templates/emails/<template>.html e envia para `para`."""
    destinatarios = [para] if isinstance(para, str) else list(para)
    contexto = {
        **contexto,
        "assunto": assunto,
        "site_url": request.build_absolute_uri("/").rstrip("/"),
    }
    html = render_to_string(f"emails/{template}.html", contexto, request=request)
    texto = strip_tags(html)
    # strip_tags deixa muitas linhas em branco; compacta o texto puro.
    texto = "\n".join(linha.strip() for linha in texto.splitlines() if linha.strip())

    mensagem = EmailMultiAlternatives(
        subject=f"{assunto} | contratempo",
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios,
    )
    mensagem.attach_alternative(html, "text/html")
    try:
        mensagem.send()
    except Exception as erro:  # SMTP fora do ar, credencial errada, etc.
        logger.error(
            "Falha ao enviar e-mail '%s' para %s: %s: %s\n  -> %s",
            assunto, destinatarios, type(erro).__name__, erro, explicar_erro_email(erro),
        )
        return False
    return True


def explicar_erro_email(erro):
    """Tradução, para quem administra o site, dos erros mais comuns do Gmail e do Brevo."""
    from .email_brevo import BrevoErro

    if isinstance(erro, BrevoErro):
        if erro.status == 401:
            return "O Brevo não reconheceu a chave. Confira BREVO_API_KEY no .env (gere outra em Brevo > SMTP & API > API Keys)."
        if "sender" in (erro.mensagem or "").lower():
            return (
                "O Brevo recusou o remetente. O e-mail de EMAIL_HOST_USER precisa estar confirmado no Brevo "
                "(Senders, domains & IPs > Senders > Add a sender)."
            )
        if erro.status == 403:
            return "A conta do Brevo ainda não foi liberada para enviar (ativação pendente) ou passou do limite diário."
        return "O Brevo recusou o envio; a mensagem dele está acima."
    if isinstance(erro, smtplib.SMTPServerDisconnected):
        return (
            "O Gmail derrubou a conexão no login. No PythonAnywhere grátis isso acontece mesmo com a senha certa: "
            "use o Brevo (coloque BREVO_API_KEY no .env; veja .env.exemplo)."
        )
    if isinstance(erro, smtplib.SMTPAuthenticationError):
        return (
            "O Gmail recusou o login. Use uma SENHA DE APP de 16 letras (Conta Google > Segurança > "
            "Senhas de app; exige verificação em duas etapas ativada), não a senha normal da conta, e "
            "confira se EMAIL_HOST_USER é o mesmo Gmail em que a senha de app foi criada."
        )
    if isinstance(erro, smtplib.SMTPSenderRefused):
        return "O Gmail recusou o remetente: EMAIL_HOST_USER precisa ser o endereço da conta que autentica."
    if isinstance(erro, smtplib.SMTPRecipientsRefused):
        return "O endereço de destino foi recusado. Confira se o e-mail do usuário está correto."
    if isinstance(erro, (TimeoutError, socket.timeout, ConnectionError, socket.gaierror)):
        return "Sem conexão com smtp.gmail.com:587. Verifique a internet, firewall ou antivírus."
    if isinstance(erro, ssl.SSLError):
        return "Falha no certificado TLS. Antivírus que inspecionam conexões costumam causar isso."
    return "Rode `python manage.py testar_email seu@email.com` para diagnosticar."


# ----- CONTA -----

def enviar_confirmacao_cadastro(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    link = request.build_absolute_uri(
        reverse("confirmar_email", args=[uid, token_confirmacao.make_token(usuario)])
    )
    return enviar_email(request, "Confirme seu e-mail", "confirmar_email", {
        "usuario": usuario, "link": link,
    }, usuario.email)


# ----- PEDIDOS -----

def _url(request, nome, *args):
    return request.build_absolute_uri(reverse(nome, args=args))


def enviar_confirmacao_compra(request, comprador, pedidos):
    total = sum(p.valor_total for p in pedidos)
    return enviar_email(request, "Recebemos sua compra", "compra_confirmada", {
        "usuario": comprador, "pedidos": pedidos, "total": total,
        "link": _url(request, "pedidos"),
    }, comprador.email)


def enviar_aviso_venda(request, pedido):
    return enviar_email(request, f"Nova venda — pedido #{pedido.id}", "nova_venda", {
        "pedido": pedido, "usuario": pedido.vendedor,
        "link": _url(request, "venda_detalhe", pedido.id),
    }, pedido.vendedor.email)


def enviar_atualizacao_pedido(request, pedido):
    """Avisa o comprador sobre a mudança de status do pedido."""
    return enviar_email(request, f"Pedido #{pedido.id}: {pedido.get_status_pedido_display().lower()}",
                        "pedido_atualizado", {
                            "pedido": pedido, "usuario": pedido.usuario,
                            "link": _url(request, "pedido_detalhe", pedido.id),
                        }, pedido.usuario.email)


def enviar_cancelamento_ao_vendedor(request, pedido):
    return enviar_email(request, f"Pedido #{pedido.id} cancelado pelo comprador", "pedido_cancelado_vendedor", {
        "pedido": pedido, "usuario": pedido.vendedor,
        "link": _url(request, "venda_detalhe", pedido.id),
    }, pedido.vendedor.email)


# ----- PERGUNTAS -----

def enviar_nova_pergunta(request, pergunta):
    vendedor = pergunta.produto.vendedor
    return enviar_email(request, "Você recebeu uma pergunta", "nova_pergunta", {
        "pergunta": pergunta, "usuario": vendedor,
        "link": _url(request, "perguntas_recebidas"),
    }, vendedor.email)


def enviar_pergunta_respondida(request, pergunta):
    return enviar_email(request, "Sua pergunta foi respondida", "pergunta_respondida", {
        "pergunta": pergunta, "usuario": pergunta.usuario,
        "link": _url(request, "produto_detalhe", pergunta.produto_id) + "#perguntas",
    }, pergunta.usuario.email)
