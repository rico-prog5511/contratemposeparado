"""
marketplace/views_conta.py

Autenticação e área "Minha conta": login, cadastro, logout, perfil,
edição de dados, senha, endereços e formas de pagamento.
"""

import time

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from .emails import enviar_confirmacao_cadastro, token_confirmacao
from .forms import CadastroForm, CartaoEdicaoForm, CartaoForm, EnderecoForm, LoginForm, PerfilForm
from .imagens import salvar_foto_perfil
from .models import Endereco, FormaPagamento, Pedido, Produto, Usuario

SESSAO_REENVIO = "ultimo_envio_confirmacao"
INTERVALO_REENVIO = 60  # segundos entre reenvios do link de confirmação


def _proximo(request, padrao):
    """Destino pós-ação: ?next= (se for do próprio site) ou o padrão."""
    proximo = request.POST.get("next") or request.GET.get("next")
    if proximo and url_has_allowed_host_and_scheme(
        proximo, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return proximo
    return reverse(padrao) if padrao and not padrao.startswith("/") else padrao


def _next_seguro(request):
    """O ?next= só volta para o template se apontar para o próprio site."""
    proximo = request.GET.get("next", "")
    if proximo and url_has_allowed_host_and_scheme(
        proximo, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return proximo
    return ""



def _breadcrumbs_conta(*itens):
    return [{"label": "Minha conta", "url": reverse("perfil")}, *itens]


# =====================================================================
# LOGIN / CADASTRO / LOGOUT
# =====================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect(_proximo(request, "perfil"))

    form = LoginForm(request.POST or None)
    email_pendente = None
    if request.method == "POST" and form.is_valid():
        usuario = authenticate(
            request,
            username=form.cleaned_data["email"],
            password=form.cleaned_data["senha"],
        )
        if usuario is None:
            form.add_error(None, "E-mail ou senha incorretos.")
        elif not usuario.email_confirmado:
            email_pendente = usuario.email
        elif usuario.status_conta == "suspenso":
            form.add_error(None, "Esta conta está suspensa. Fale com o suporte pela página de contato.")
        else:
            login(request, usuario)
            if not form.cleaned_data["lembrar"]:
                request.session.set_expiry(0)  # expira ao fechar o navegador
            messages.success(request, f"Bem-vindo(a) de volta, {usuario.nome_completo.split()[0]}!")
            return redirect(_proximo(request, "perfil"))

    return render(request, "conta/login.html", {
        "form": form,
        "next": _next_seguro(request),
        "email_pendente": email_pendente,
    })


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("perfil")

    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = Usuario.objects.create_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["senha"],
            nome_completo=form.cleaned_data["nome_completo"].strip(),
            email_confirmado=False,
        )
        enviado = enviar_confirmacao_cadastro(request, usuario)
        request.session[SESSAO_REENVIO] = time.time()
        return render(request, "conta/verifique_email.html", {
            "email": usuario.email,
            "falha_envio": not enviado,
        })

    return render(request, "conta/cadastro.html", {
        "form": form,
        "next": _next_seguro(request),
    })


def confirmar_email(request, uidb64, token):
    try:
        usuario = Usuario.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (Usuario.DoesNotExist, ValueError, TypeError, OverflowError):
        usuario = None

    if usuario and usuario.email_confirmado:
        messages.info(request, "Este e-mail já estava confirmado. É só entrar.")
        return redirect("login")

    if usuario is None or not token_confirmacao.check_token(usuario, token):
        return render(request, "conta/confirmacao_invalida.html", status=400)

    usuario.email_confirmado = True
    usuario.save(update_fields=["email_confirmado"])
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "E-mail confirmado! Sua conta está ativa. Boas-vindas à contratempo!")
    return redirect("perfil")


@require_POST
def reenviar_confirmacao(request):
    """
    Reenvia o link de confirmação. A resposta é sempre a mesma, exista
    ou não a conta, para não revelar quais e-mails estão cadastrados.
    Limite: um envio por minuto por sessão.
    """
    ultimo = request.session.get(SESSAO_REENVIO, 0)
    if time.time() - ultimo < INTERVALO_REENVIO:
        messages.error(request, "Aguarde um minuto antes de pedir um novo e-mail.")
        return redirect("login")

    email = (request.POST.get("email") or "").strip().lower()
    usuario = Usuario.objects.filter(email__iexact=email, is_active=True, email_confirmado=False).first()
    if usuario:
        enviar_confirmacao_cadastro(request, usuario)
    request.session[SESSAO_REENVIO] = time.time()
    messages.success(request, f"Se houver um cadastro pendente para {email}, um novo link foi enviado.")
    return redirect("login")


# ---------------------------------------------------------------------
# RECUPERAÇÃO DE SENHA — fluxo nativo do Django com templates próprios
# ---------------------------------------------------------------------

class RecuperarSenhaView(auth_views.PasswordResetView):
    template_name = "conta/senha_reset_form.html"
    email_template_name = "emails/senha_reset.txt"
    html_email_template_name = "emails/senha_reset.html"
    subject_template_name = "emails/senha_reset_assunto.txt"
    success_url = reverse_lazy("password_reset_done")

    def form_valid(self, form):
        self.extra_email_context = {
            "assunto": "Crie sua nova senha",
            "site_url": self.request.build_absolute_uri("/").rstrip("/"),
        }
        return super().form_valid(form)


class RecuperarSenhaEnviadoView(auth_views.PasswordResetDoneView):
    template_name = "conta/senha_reset_enviado.html"


class NovaSenhaView(auth_views.PasswordResetConfirmView):
    template_name = "conta/senha_reset_confirmar.html"
    success_url = reverse_lazy("password_reset_complete")

    def form_valid(self, form):
        resposta = super().form_valid(form)
        # Quem recebeu o link no e-mail provou que o e-mail é dele.
        if not self.user.email_confirmado:
            self.user.email_confirmado = True
            self.user.save(update_fields=["email_confirmado"])
        return resposta


class NovaSenhaConcluidaView(auth_views.PasswordResetCompleteView):
    template_name = "conta/senha_reset_concluido.html"


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Você saiu da sua conta.")
    return redirect("home")


# =====================================================================
# PERFIL
# =====================================================================

@login_required
def perfil(request):
    usuario = request.user
    pedidos_recentes = (
        Pedido.objects.filter(usuario=usuario)
        .prefetch_related("itens")
        .order_by("-data_criacao")[:3]
    )
    return render(request, "conta/perfil.html", {
        "pedidos_recentes": pedidos_recentes,
        "total_pedidos": Pedido.objects.filter(usuario=usuario).count(),
        "total_anuncios_ativos": Produto.objects.filter(vendedor=usuario, status_anuncio="ativo").count(),
        "total_enderecos": usuario.enderecos.count(),
        "endereco_principal": usuario.enderecos.filter(endereco_principal=True).first(),
        "breadcrumbs": [{"label": "Minha conta", "url": None}],
    })


@login_required
def editar_perfil(request):
    form = PerfilForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        usuario = form.save(commit=False)
        if request.POST.get("remover_avatar"):
            usuario.avatar = None
        arquivo = form.cleaned_data.get("avatar_arquivo")
        if arquivo:
            usuario.avatar = salvar_foto_perfil(arquivo)
        usuario.save()
        messages.success(request, "Seus dados foram atualizados.")
        return redirect("perfil")

    return render(request, "conta/editar.html", {
        "form": form,
        "breadcrumbs": _breadcrumbs_conta({"label": "Editar perfil", "url": None}),
    })


@login_required
def alterar_senha(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    form.fields["old_password"].label = "Senha atual"
    form.fields["new_password1"].label = "Nova senha"
    form.fields["new_password2"].label = "Confirmar nova senha"

    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        update_session_auth_hash(request, usuario)  # mantém o usuário logado
        messages.success(request, "Senha alterada com sucesso.")
        return redirect("perfil")

    return render(request, "conta/senha.html", {
        "form": form,
        "breadcrumbs": _breadcrumbs_conta({"label": "Alterar senha", "url": None}),
    })


@login_required
@require_POST
def desativar_conta(request):
    usuario = request.user
    if Produto.objects.filter(vendedor=usuario, status_anuncio="ativo").exists():
        messages.error(request, "Pause ou encerre seus anúncios ativos antes de desativar a conta.")
        return redirect("editar_perfil")
    usuario.desativar_conta()
    logout(request)
    messages.success(request, "Sua conta foi desativada. Sentiremos sua falta!")
    return redirect("home")


# =====================================================================
# ENDEREÇOS
# =====================================================================

def _definir_endereco_principal(endereco):
    Endereco.objects.filter(usuario_id=endereco.usuario_id).exclude(pk=endereco.pk).update(endereco_principal=False)
    if not endereco.endereco_principal:
        endereco.endereco_principal = True
        endereco.save(update_fields=["endereco_principal"])


@login_required
def enderecos(request):
    lista = request.user.enderecos.order_by("-endereco_principal", "nome_endereco")
    return render(request, "conta/enderecos.html", {
        "enderecos": lista,
        "breadcrumbs": _breadcrumbs_conta({"label": "Endereços", "url": None}),
    })


@login_required
def endereco_form(request, endereco_id=None):
    endereco = None
    if endereco_id:
        endereco = get_object_or_404(Endereco, pk=endereco_id, usuario=request.user)

    form = EnderecoForm(request.POST or None, instance=endereco)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            novo = form.save(commit=False)
            novo.usuario = request.user
            primeiro = not request.user.enderecos.exclude(pk=novo.pk).exists()
            novo.save()
            if novo.endereco_principal or primeiro:
                _definir_endereco_principal(novo)
        messages.success(request, "Endereço salvo.")
        return redirect(_proximo(request, "enderecos"))

    titulo = "Editar endereço" if endereco else "Novo endereço"
    return render(request, "conta/endereco_form.html", {
        "form": form,
        "endereco": endereco,
        "titulo": titulo,
        "next": _next_seguro(request),
        "breadcrumbs": _breadcrumbs_conta(
            {"label": "Endereços", "url": reverse("enderecos")},
            {"label": titulo, "url": None},
        ),
    })


@login_required
@require_POST
def endereco_excluir(request, endereco_id):
    endereco = get_object_or_404(Endereco, pk=endereco_id, usuario=request.user)
    era_principal = endereco.endereco_principal
    endereco.delete()  # pedidos guardam endereco_snapshot, então o histórico é preservado
    if era_principal:
        outro = request.user.enderecos.order_by("data_cadastro").first()
        if outro:
            _definir_endereco_principal(outro)
    messages.success(request, "Endereço excluído.")
    return redirect("enderecos")


@login_required
@require_POST
def endereco_principal(request, endereco_id):
    endereco = get_object_or_404(Endereco, pk=endereco_id, usuario=request.user)
    _definir_endereco_principal(endereco)
    messages.success(request, f'"{endereco.nome_endereco}" agora é seu endereço principal.')
    return redirect(_proximo(request, "enderecos"))


# =====================================================================
# FORMAS DE PAGAMENTO
# =====================================================================

def _definir_pagamento_principal(forma):
    FormaPagamento.objects.filter(usuario_id=forma.usuario_id).exclude(pk=forma.pk).update(principal=False)
    if not forma.principal:
        forma.principal = True
        forma.save(update_fields=["principal"])


@login_required
def pagamentos(request):
    lista = request.user.formas_pagamento.order_by("-principal", "-data_cadastro")
    return render(request, "conta/pagamentos.html", {
        "formas": lista,
        "breadcrumbs": _breadcrumbs_conta({"label": "Formas de pagamento", "url": None}),
    })


@login_required
def pagamento_form(request, forma_id=None):
    forma = None
    if forma_id:
        forma = get_object_or_404(FormaPagamento, pk=forma_id, usuario=request.user)

    Formulario = CartaoEdicaoForm if forma else CartaoForm
    form = Formulario(request.POST or None, instance=forma)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            nova = form.save(commit=False)
            nova.usuario = request.user
            primeira = not request.user.formas_pagamento.exclude(pk=nova.pk).exists()
            nova.save()
            if nova.principal or primeira:
                _definir_pagamento_principal(nova)
        messages.success(request, "Cartão salvo.")
        return redirect(_proximo(request, "pagamentos"))

    titulo = "Editar cartão" if forma else "Novo cartão"
    return render(request, "conta/pagamento_form.html", {
        "form": form,
        "forma": forma,
        "titulo": titulo,
        "next": _next_seguro(request),
        "breadcrumbs": _breadcrumbs_conta(
            {"label": "Formas de pagamento", "url": reverse("pagamentos")},
            {"label": titulo, "url": None},
        ),
    })


@login_required
@require_POST
def pagamento_excluir(request, forma_id):
    forma = get_object_or_404(FormaPagamento, pk=forma_id, usuario=request.user)
    era_principal = forma.principal
    forma.delete()  # pedidos guardam forma_pagamento_snapshot
    if era_principal:
        outra = request.user.formas_pagamento.order_by("data_cadastro").first()
        if outra:
            _definir_pagamento_principal(outra)
    messages.success(request, "Forma de pagamento excluída.")
    return redirect("pagamentos")


@login_required
@require_POST
def pagamento_principal(request, forma_id):
    forma = get_object_or_404(FormaPagamento, pk=forma_id, usuario=request.user)
    _definir_pagamento_principal(forma)
    messages.success(request, "Forma de pagamento principal atualizada.")
    return redirect(_proximo(request, "pagamentos"))
