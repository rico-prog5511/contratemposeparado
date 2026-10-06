"""
marketplace/forms.py

Formulários do contratempo. Todos os campos correspondem aos Models de
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
    rotulo_marca,
)
from .sku import EXEMPLO as EXEMPLO_SKU
from .sku import PADRAO as PADRAO_SKU
from .sku import normalizar_sku

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


def _so_digitos(valor):
    return "".join(c for c in (valor or "") if c.isdigit())


def validar_cvv(valor, bandeira):
    """Devolve o CVV só com dígitos: 4 no American Express, 3 nos demais."""
    cvv = (valor or "").strip()
    tamanho = 4 if bandeira == "American Express" else 3
    if not (cvv.isdigit() and len(cvv) == tamanho):
        raise forms.ValidationError(f"O código de segurança tem {tamanho} dígitos.")
    return cvv


class ValidadeField(forms.CharField):
    """Validade no formato MM/AA (ou MM/AAAA). Devolve (mês, ano com 4 dígitos)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("label", "Validade")
        kwargs.setdefault("max_length", 7)
        kwargs.setdefault("widget", forms.TextInput(attrs={
            "placeholder": "MM/AA", "inputmode": "numeric", "autocomplete": "cc-exp",
            "data-mascara": "validade",
        }))
        super().__init__(**kwargs)

    def prepare_value(self, value):
        if isinstance(value, tuple):
            return f"{value[0]:02d}/{value[1] % 100:02d}"
        return value

    def clean(self, value):
        texto = super().clean(value)
        if texto in self.empty_values:
            return None
        partes = texto.replace(" ", "").split("/")
        if len(partes) != 2 or not all(p.isdigit() for p in partes) or len(partes[1]) not in (2, 4):
            raise forms.ValidationError("Use o formato MM/AA, como está no cartão.")
        mes, ano = int(partes[0]), int(partes[1])
        if not 1 <= mes <= 12:
            raise forms.ValidationError("O mês da validade vai de 01 a 12.")
        return mes, (2000 + ano if ano < 100 else ano)


class CartaoForm(forms.ModelForm):
    """
    Cadastro de cartão. Pede os dados como uma loja de verdade, mas o
    número completo e o CVV só são conferidos e DESCARTADOS: o banco
    guarda apenas bandeira, 4 últimos dígitos e validade.
    `token_externo` fica para a integração com um gateway de pagamento.
    """

    tipo = forms.ChoiceField(
        label="Tipo", choices=FormaPagamento.TIPO_CHOICES, initial="cartao_credito", widget=forms.RadioSelect,
    )
    numero = forms.CharField(
        label="Número do cartão", max_length=23,
        widget=forms.TextInput(attrs={
            "placeholder": "0000 0000 0000 0000", "inputmode": "numeric",
            "autocomplete": "cc-number", "data-mascara": "cartao",
        }),
    )
    nome_titular = forms.CharField(
        label="Nome impresso no cartão", max_length=60,
        widget=forms.TextInput(attrs={"autocomplete": "cc-name", "placeholder": "Como aparece no cartão"}),
    )
    bandeira = forms.ChoiceField(
        label="Bandeira", choices=[("", "Selecione")] + FormaPagamento.BANDEIRA_CHOICES,
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )
    validade = ValidadeField()
    cvv = forms.CharField(
        label="CVV", max_length=4, help_text="3 dígitos no verso (4 na frente, no American Express).",
        widget=forms.PasswordInput(attrs={
            "inputmode": "numeric", "autocomplete": "cc-csc", "placeholder": "•••", "data-mascara": "cvv",
        }),
    )

    class Meta:
        model = FormaPagamento
        fields = ["tipo", "bandeira", "apelido", "principal"]
        labels = {
            "apelido": "Apelido (opcional)",
            "principal": "Usar como forma de pagamento principal",
        }
        widgets = {
            "apelido": forms.TextInput(attrs={"placeholder": "Ex.: Cartão do banco X"}),
        }

    def clean_numero(self):
        numero = _so_digitos(self.cleaned_data["numero"])
        if not 13 <= len(numero) <= 19:
            raise forms.ValidationError("O número do cartão tem de 13 a 19 dígitos.")
        return numero

    def clean(self):
        dados = super().clean()
        if "cvv" in dados and dados.get("bandeira"):
            try:
                validar_cvv(dados["cvv"], dados["bandeira"])
            except forms.ValidationError as erro:
                self.add_error("cvv", erro)
        return dados

    def save(self, commit=True):
        cartao = super().save(commit=False)
        cartao.ultimos_digitos = self.cleaned_data["numero"][-4:]
        cartao.validade_mes, cartao.validade_ano = self.cleaned_data["validade"]
        if commit:
            cartao.save()
        return cartao


class CartaoEdicaoForm(forms.ModelForm):
    """Edição de um cartão salvo: o número não muda, só apelido, validade e principal."""

    validade = ValidadeField(help_text="Atualize quando chegar o cartão novo.")

    class Meta:
        model = FormaPagamento
        fields = ["apelido", "principal"]
        labels = CartaoForm.Meta.labels
        widgets = CartaoForm.Meta.widgets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.validade_mes and self.instance.validade_ano:
            self.initial["validade"] = (self.instance.validade_mes, self.instance.validade_ano)

    def save(self, commit=True):
        cartao = super().save(commit=False)
        cartao.validade_mes, cartao.validade_ano = self.cleaned_data["validade"]
        if commit:
            cartao.save()
        return cartao


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
        help_text=f"Até {LIMITE_IMAGENS_ANUNCIO} imagens (JPG, PNG ou WEBP, máx. 5 MB cada). "
                  "Pode escolher uma por vez ou várias juntas: elas vão se somando.",
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
            "marca": "Marca / autor",  # muda conforme a categoria (ver __init__)
            "ano": "Ano",
            "preco": "Preço (R$)",
            "quantidade_disponivel": "Estoque",
            "sku": "Código (SKU)",
            "status_anuncio": "Status",
        }
        help_texts = {
            "quantidade_disponivel": "Quantas unidades você tem para vender.",
        }
        error_messages = {
            # O banco não deixa dois anúncios (de qualquer vendedor) com o mesmo código.
            "sku": {"unique": "Este código já está em uso. Escolha outro ou deixe em branco para o site gerar um."},
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
        self.tamanho_maximo_imagem = TAMANHO_MAXIMO_IMAGEM  # o upload.js avisa antes de enviar

        # SKU no padrão XXX-XXX-XXX (ver sku.py). Ao criar, em branco = gerado pelo site.
        self.fields["sku"].help_text = (
            f"Opcional. Formato: 3 partes de 3 letras ou números, como {EXEMPLO_SKU}. "
            + ("Deixe em branco para o anúncio ficar sem código." if self.instance.pk
               else "Se deixar em branco, o site gera um automaticamente.")
        )
        self.fields["sku"].widget.attrs.update({
            # 11 = XXX-XXX-XXX; um código antigo mais longo continua cabendo no campo.
            "placeholder": f"Ex.: {EXEMPLO_SKU}", "maxlength": max(11, len(self.instance.sku or "")),
            "autocapitalize": "characters", "spellcheck": "false", "class": "mono",
        })

        categorias = Categoria.objects.filter(ativo=True).order_by("nome")
        self.fields["categoria"].queryset = categorias
        self.fields["categoria"].empty_label = "Selecione uma categoria"

        # Nome do campo "marca" conforme a categoria: "Autor / editora" em
        # Quadrinhos, "Artista / banda" em Discos... O JavaScript troca na
        # hora (anuncios/form.html); aqui vale para a página já carregada.
        self.rotulos_marca = {
            str(c.id): dict(zip(("rotulo", "exemplo"), rotulo_marca(c))) for c in categorias
        }
        self.rotulos_marca[""] = dict(zip(("rotulo", "exemplo"), rotulo_marca(None)))
        escolhida = str(self.data.get("categoria", "") if self.is_bound
                        else self.initial.get("categoria") or self.instance.categoria_id or "")
        atual = self.rotulos_marca.get(escolhida, self.rotulos_marca[""])
        self.fields["marca"].label = atual["rotulo"]
        self.fields["marca"].widget.attrs.update({"placeholder": atual["exemplo"], "data-marca-campo": ""})
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
        digitado = (self.cleaned_data.get("sku") or "").strip()
        if not digitado:
            return None
        # Anúncio antigo com código fora do padrão: continua valendo se não mudou.
        if self.instance.pk and digitado == self.instance.sku:
            return digitado
        sku = normalizar_sku(digitado)
        if not PADRAO_SKU.match(sku):
            raise forms.ValidationError(
                f"Use o formato XXX-XXX-XXX: 3 partes de 3 letras ou números separadas por hífen "
                f"(ex.: {EXEMPLO_SKU}). Ou deixe em branco."
            )
        return sku

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
