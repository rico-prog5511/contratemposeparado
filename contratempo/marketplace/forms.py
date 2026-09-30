"""
marketplace/forms.py

Formulários do Contratempo. Todos os campos correspondem aos Models de
marketplace/models.py — nenhum campo novo foi criado no banco.
"""

from datetime import date

from django import forms
from django.contrib.auth import password_validation

from .models import (
    Categoria,
    Contato,
    Endereco,
    FormaPagamento,
    Franquia,
    Produto,
    Usuario,
)

LIMITE_IMAGENS_ANUNCIO = 8
TAMANHO_MAXIMO_IMAGEM = 5 * 1024 * 1024  # 5 MB


# =====================================================================
# UPLOAD DE VÁRIAS IMAGENS
# =====================================================================

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """ImageField que aceita vários arquivos (padrão da documentação do Django)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages["required"], code="required")
            return []
        arquivos = data if isinstance(data, (list, tuple)) else [data]
        limpar = super().clean
        return [limpar(arquivo, initial) for arquivo in arquivos]


def validar_tamanho_imagem(arquivo):
    if arquivo and arquivo.size > TAMANHO_MAXIMO_IMAGEM:
        raise forms.ValidationError(
            f'"{arquivo.name}" tem mais de 5 MB. Envie uma imagem menor.'
        )


# =====================================================================
# CONTA
# =====================================================================

class LoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Digite seu e-mail"}),
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "Digite sua senha"}),
    )
    lembrar = forms.BooleanField(label="Lembrar de mim", required=False)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class CadastroForm(forms.Form):
    nome_completo = forms.CharField(
        label="Nome completo",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Digite seu nome completo"}),
    )
    email = forms.EmailField(
        label="E-mail",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Digite seu e-mail"}),
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Crie uma senha"}),
        help_text="Mínimo de 8 caracteres, sem ser só números.",
    )
    confirmar_senha = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Digite a senha novamente"}),
    )
    termos = forms.BooleanField(
        label="Li e concordo com a política de privacidade.",
        error_messages={"required": "Você precisa aceitar a política de privacidade."},
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        dados = super().clean()
        senha = dados.get("senha")
        confirmar = dados.get("confirmar_senha")
        if senha and confirmar and senha != confirmar:
            self.add_error("confirmar_senha", "As senhas não coincidem.")
        if senha:
            usuario_temp = Usuario(
                email=dados.get("email", ""),
                nome_completo=dados.get("nome_completo", ""),
            )
            try:
                password_validation.validate_password(senha, usuario_temp)
            except forms.ValidationError as erro:
                self.add_error("senha", erro)
        return dados


class PerfilForm(forms.ModelForm):
    avatar_arquivo = forms.ImageField(
        label="Foto de perfil",
        required=False,
        validators=[validar_tamanho_imagem],
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )

    class Meta:
        model = Usuario
        fields = ["nome_completo", "email", "telefone", "data_nascimento"]
        labels = {
            "nome_completo": "Nome completo",
            "email": "E-mail",
            "telefone": "Telefone",
            "data_nascimento": "Data de nascimento",
        }
        widgets = {
            "telefone": forms.TextInput(attrs={
                "placeholder": "(00) 00000-0000", "autocomplete": "tel", "data-mask": "telefone",
            }),
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existe = Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists()
        if existe:
            raise forms.ValidationError("Este e-mail já está em uso por outra conta.")
        return email

    def clean_data_nascimento(self):
        data = self.cleaned_data.get("data_nascimento")
        if data and data > date.today():
            raise forms.ValidationError("A data de nascimento não pode estar no futuro.")
        return data


class EnderecoForm(forms.ModelForm):
    class Meta:
        model = Endereco
        fields = [
            "nome_endereco", "cep", "logradouro", "numero", "complemento",
            "bairro", "cidade", "estado", "endereco_principal",
        ]
        labels = {
            "nome_endereco": "Nome do endereço",
            "cep": "CEP",
            "logradouro": "Rua / Avenida",
            "numero": "Número",
            "complemento": "Complemento",
            "bairro": "Bairro",
            "cidade": "Cidade",
            "estado": "UF",
            "endereco_principal": "Usar como endereço principal",
        }
        widgets = {
            "nome_endereco": forms.TextInput(attrs={"placeholder": "Ex.: Casa, Trabalho"}),
            "cep": forms.TextInput(attrs={
                "placeholder": "00000-000", "inputmode": "numeric",
                "autocomplete": "postal-code", "data-mask": "cep", "data-cep-lookup": "",
            }),
            "logradouro": forms.TextInput(attrs={"autocomplete": "address-line1", "data-cep-field": "logradouro"}),
            "numero": forms.TextInput(attrs={"inputmode": "numeric"}),
            "complemento": forms.TextInput(attrs={"placeholder": "Apto, bloco… (opcional)", "autocomplete": "address-line2"}),
            "bairro": forms.TextInput(attrs={"data-cep-field": "bairro"}),
            "cidade": forms.TextInput(attrs={"autocomplete": "address-level2", "data-cep-field": "localidade"}),
            "estado": forms.TextInput(attrs={
                "maxlength": 2, "placeholder": "SP", "autocomplete": "address-level1", "data-cep-field": "uf",
            }),
        }

    def clean_estado(self):
        estado = self.cleaned_data["estado"].strip().upper()
        if len(estado) != 2 or not estado.isalpha():
            raise forms.ValidationError("Informe a sigla do estado com 2 letras (ex.: SP).")
        return estado

    def clean_cep(self):
        digitos = "".join(c for c in self.cleaned_data["cep"] if c.isdigit())
        if len(digitos) != 8:
            raise forms.ValidationError("O CEP precisa ter 8 dígitos.")
        return f"{digitos[:5]}-{digitos[5:]}"


class FormaPagamentoForm(forms.ModelForm):
    """
    Guarda apenas dados NÃO sensíveis (apelido, bandeira e últimos 4
    dígitos). O número completo do cartão nunca passa pelo Contratempo:
    `token_externo` deve ser preenchido pela integração com o gateway de
    pagamento, quando ela existir.
    """

    class Meta:
        model = FormaPagamento
        fields = ["tipo", "apelido", "bandeira", "ultimos_digitos", "principal"]
        labels = {
            "tipo": "Tipo",
            "apelido": "Apelido",
            "bandeira": "Bandeira",
            "ultimos_digitos": "Últimos 4 dígitos",
            "principal": "Usar como forma de pagamento principal",
        }
        widgets = {
            "tipo": forms.RadioSelect,
            "apelido": forms.TextInput(attrs={"placeholder": "Ex.: Cartão do banco X"}),
            "bandeira": forms.TextInput(attrs={"placeholder": "Ex.: Visa, Mastercard"}),
            "ultimos_digitos": forms.TextInput(attrs={
                "placeholder": "0000", "inputmode": "numeric", "maxlength": 4,
            }),
        }

    def clean(self):
        dados = super().clean()
        tipo = dados.get("tipo")
        digitos = (dados.get("ultimos_digitos") or "").strip()
        if tipo in ("cartao_credito", "cartao_debito"):
            if not (len(digitos) == 4 and digitos.isdigit()):
                self.add_error("ultimos_digitos", "Informe os 4 últimos dígitos do cartão.")
            if not (dados.get("bandeira") or "").strip():
                self.add_error("bandeira", "Informe a bandeira do cartão.")
        else:
            dados["ultimos_digitos"] = None
            dados["bandeira"] = None
        return dados


# =====================================================================
# CONTATO
# =====================================================================

class ContatoForm(forms.ModelForm):
    ASSUNTOS = [
        ("", "Selecione um assunto"),
        ("Pedido", "Pedido"),
        ("Dúvida sobre produto", "Dúvida sobre produto"),
        ("Pagamento", "Pagamento"),
        ("Entrega", "Entrega"),
        ("Anúncios e vendas", "Anúncios e vendas"),
        ("Privacidade e dados", "Privacidade e dados"),
        ("Outro", "Outro"),
    ]

    assunto = forms.ChoiceField(label="Assunto", choices=ASSUNTOS)

    class Meta:
        model = Contato
        fields = ["nome", "email", "assunto", "mensagem"]
        labels = {"nome": "Nome", "email": "E-mail", "mensagem": "Mensagem"}
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Seu nome", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Seu e-mail", "autocomplete": "email"}),
            "mensagem": forms.Textarea(attrs={"rows": 6, "placeholder": "Escreva sua mensagem…"}),
        }


# =====================================================================
# ANÚNCIOS
# =====================================================================

class ProdutoForm(forms.ModelForm):
    imagens = MultipleImageField(
        label="Adicionar imagens",
        required=False,
        help_text=f"Até {LIMITE_IMAGENS_ANUNCIO} imagens (JPG, PNG ou WEBP, máx. 5 MB cada).",
    )

    class Meta:
        model = Produto
        fields = [
            "nome", "categoria", "franquia", "descricao", "condicao",
            "marca", "ano", "preco", "quantidade_disponivel", "sku", "status_anuncio",
        ]
        labels = {
            "nome": "Título do anúncio",
            "categoria": "Categoria",
            "franquia": "Franquia",
            "descricao": "Descrição",
            "condicao": "Condição",
            "marca": "Marca / fabricante",
            "ano": "Ano",
            "preco": "Preço (R$)",
            "quantidade_disponivel": "Estoque",
            "sku": "Código (SKU)",
            "status_anuncio": "Status",
        }
        help_texts = {
            "sku": "Opcional. Código interno para você identificar o item.",
            "quantidade_disponivel": "Quantas unidades você tem para vender.",
        }
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Action Figure Naruto — Bandai, 17 cm"}),
            "descricao": forms.Textarea(attrs={
                "rows": 7, "placeholder": "Estado de conservação, medidas, itens inclusos, detalhes de colecionador…",
            }),
            "preco": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "placeholder": "0,00"}),
            "quantidade_disponivel": forms.NumberInput(attrs={"min": "0"}),
            "ano": forms.NumberInput(attrs={"placeholder": "Ex.: 1998"}),
            "condicao": forms.RadioSelect,
            "status_anuncio": forms.RadioSelect,
        }

    def __init__(self, *args, imagens_existentes=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.imagens_existentes = imagens_existentes
        self.fields["categoria"].queryset = Categoria.objects.filter(ativo=True).order_by("nome")
        self.fields["categoria"].empty_label = "Selecione uma categoria"
        self.fields["franquia"].queryset = Franquia.objects.filter(ativo=True).order_by("nome")
        self.fields["franquia"].empty_label = "Nenhuma / não se aplica"
        # "vendido" é definido pelo sistema quando o estoque zera.
        self.fields["status_anuncio"].choices = [
            (valor, rotulo) for valor, rotulo in Produto.STATUS_CHOICES if valor != "vendido"
        ] if self.instance.status_anuncio != "vendido" else Produto.STATUS_CHOICES

    def clean_preco(self):
        preco = self.cleaned_data["preco"]
        if preco is not None and preco <= 0:
            raise forms.ValidationError("O preço precisa ser maior que zero.")
        return preco

    def clean_ano(self):
        ano = self.cleaned_data.get("ano")
        if ano is not None and not (1900 <= ano <= date.today().year + 1):
            raise forms.ValidationError("Informe um ano válido.")
        return ano

    def clean_sku(self):
        # SKU é UNIQUE e aceita NULL: string vazia viraria duplicata.
        sku = (self.cleaned_data.get("sku") or "").strip()
        return sku or None

    def clean_imagens(self):
        imagens = self.cleaned_data.get("imagens") or []
        for imagem in imagens:
            validar_tamanho_imagem(imagem)
        if self.imagens_existentes + len(imagens) > LIMITE_IMAGENS_ANUNCIO:
            raise forms.ValidationError(
                f"Cada anúncio pode ter no máximo {LIMITE_IMAGENS_ANUNCIO} imagens."
            )
        return imagens

    def clean(self):
        dados = super().clean()
        if dados.get("status_anuncio") == "ativo" and dados.get("quantidade_disponivel") == 0:
            self.add_error("quantidade_disponivel", "Um anúncio ativo precisa ter pelo menos 1 unidade em estoque.")
        return dados


# =====================================================================
# AVALIAÇÕES
# =====================================================================

class AvaliacaoForm(forms.Form):
    """
    Form simples (não ModelForm): Avaliacao.clean() compara self.nota
    diretamente e quebraria se a nota estivesse ausente. A view monta a
    Avaliacao e chama full_clean() só depois deste form ser válido.
    """

    nota = forms.TypedChoiceField(
        label="Nota",
        coerce=int,
        choices=[(n, f"{n} estrela{'s' if n > 1 else ''}") for n in range(5, 0, -1)],
        widget=forms.RadioSelect,
    )
    comentario = forms.CharField(
        label="Comentário",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Conte como foi sua experiência (opcional)"}),
    )
