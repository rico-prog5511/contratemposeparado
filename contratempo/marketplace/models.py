from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):

    def _criar_usuario(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._criar_usuario(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("nome_completo", extra_fields.get("nome_completo", email))

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")

        return self._criar_usuario(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):

    STATUS_CONTA_CHOICES = [
        ("ativo", "Ativo"),
        ("inativo", "Inativo"),
        ("suspenso", "Suspenso"),
    ]

    id = models.BigAutoField(primary_key=True)
    nome_completo = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=128, db_column="senha")
    data_nascimento = models.DateField(null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    avatar = models.CharField(max_length=255, null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    status_conta = models.CharField(
        max_length=10, choices=STATUS_CONTA_CHOICES, default="ativo"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_confirmado = models.BooleanField(default=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.nome_completo} <{self.email}>"

    def desativar_conta(self):
        self.is_active = False
        self.status_conta = "inativo"
        self.save(update_fields=["is_active", "status_conta"])


class Endereco(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enderecos",
        db_column="usuario_id",
    )
    nome_endereco = models.CharField(max_length=100)
    cep = models.CharField(max_length=10)
    logradouro = models.CharField(max_length=150)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    pais = models.CharField(max_length=60, default="Brasil")
    endereco_principal = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "enderecos"
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"

    def __str__(self):
        return f"{self.nome_endereco} — {self.cidade}/{self.estado}"


class FormaPagamento(models.Model):

    TIPO_CHOICES = [
        ("cartao_credito", "Cartão de crédito"),
        ("cartao_debito", "Cartão de débito"),
    ]
    BANDEIRA_CHOICES = [
        ("Visa", "Visa"),
        ("Mastercard", "Mastercard"),
        ("Elo", "Elo"),
        ("American Express", "American Express"),
        ("Hipercard", "Hipercard"),
    ]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="formas_pagamento",
        db_column="usuario_id",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    apelido = models.CharField(max_length=60, null=True, blank=True)
    ultimos_digitos = models.CharField(max_length=4, null=True, blank=True)
    bandeira = models.CharField(max_length=30, choices=BANDEIRA_CHOICES, null=True, blank=True)
    validade_mes = models.PositiveSmallIntegerField(null=True, blank=True)
    validade_ano = models.PositiveSmallIntegerField(null=True, blank=True)
    token_externo = models.CharField(max_length=255, null=True, blank=True)
    principal = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "formas_pagamento"
        verbose_name = "Forma de pagamento"
        verbose_name_plural = "Formas de pagamento"

    def __str__(self):
        return self.apelido or f"{self.get_tipo_display()} ****{self.ultimos_digitos or ''}"

    @property
    def descricao(self):
        final = f"final {self.ultimos_digitos}" if self.ultimos_digitos else ""
        return " ".join(p for p in (self.get_tipo_display(), self.bandeira, final) if p)

    @property
    def validade_texto(self):
        if not (self.validade_mes and self.validade_ano):
            return ""
        return f"{self.validade_mes:02d}/{self.validade_ano % 100:02d}"

    @property
    def vencido(self):
        if not (self.validade_mes and self.validade_ano):
            return False
        hoje = timezone.localdate()
        return (self.validade_ano, self.validade_mes) < (hoje.year, hoje.month)


ROTULOS_MARCA = [
    (("livro", "quadrinho", "hq", "manga", "gibi", "revista"), "Autor / editora", "Ex.: Frank Miller, Panini"),
    (("music", "disco", "vini", "cd", "fita", "lp"), "Artista / banda", "Ex.: Legião Urbana"),
    (("filme", "cinema", "dvd", "blu", "serie"), "Diretor / estúdio", "Ex.: Studio Ghibli"),
    (("jogo", "game", "video", "console", "brinquedo", "action", "figure", "boneco", "carta", "card",
      "colecionav", "miniatura", "roupa", "vestuario"), "Marca / fabricante", "Ex.: Bandai, Nintendo"),
]
ROTULO_MARCA_PADRAO = ("Marca / autor", "Ex.: Bandai, Frank Miller")


def rotulo_marca(categoria):
    if categoria is None:
        return ROTULO_MARCA_PADRAO
    from .busca import normalizar
    texto = normalizar(f"{categoria.nome} {categoria.slug}").replace("-", " ")
    palavras_categoria = texto.split()
    for comecos, rotulo, exemplo in ROTULOS_MARCA:
        if any(p.startswith(comecos) for p in palavras_categoria):
            return rotulo, exemplo
    return ROTULO_MARCA_PADRAO


class Categoria(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "categorias"
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nome

    @property
    def rotulo_marca(self):
        return rotulo_marca(self)[0]


class Franquia(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "franquias"
        verbose_name = "Franquia"
        verbose_name_plural = "Franquias"

    def __str__(self):
        return self.nome


class Produto(models.Model):
    CONDICAO_CHOICES = [
        ("novo", "Novo"),
        ("usado", "Usado"),
        ("semi_novo", "Semi-novo"),
    ]
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("pausado", "Pausado"),
        ("vendido", "Vendido"),
        ("encerrado", "Encerrado"),
    ]

    id = models.BigAutoField(primary_key=True)
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="produtos",
        db_column="vendedor_id",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="produtos",
        db_column="categoria_id",
    )
    franquia = models.ForeignKey(
        Franquia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produtos",
        db_column="franquia_id",
    )
    nome = models.CharField(max_length=150)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade_disponivel = models.PositiveIntegerField(default=0)
    condicao = models.CharField(max_length=10, choices=CONDICAO_CHOICES, default="usado")
    marca = models.CharField(max_length=80, null=True, blank=True)
    ano = models.SmallIntegerField(null=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    status_anuncio = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ativo")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "produtos"
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome


class ProdutoImagem(models.Model):
    id = models.BigAutoField(primary_key=True)
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="imagens",
        db_column="produto_id",
    )
    url_imagem = models.CharField(max_length=255)
    principal = models.BooleanField(default=False)
    ordem_exibicao = models.SmallIntegerField(default=0)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "produto_imagens"
        verbose_name = "Imagem do produto"
        verbose_name_plural = "Imagens do produto"
        ordering = ["ordem_exibicao"]

    def save(self, *args, **kwargs):
        if self.principal:
            ProdutoImagem.objects.filter(
                produto_id=self.produto_id, principal=True
            ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Imagem de {self.produto.nome} (#{self.ordem_exibicao})"


class Carrinho(models.Model):
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("finalizado", "Finalizado"),
        ("abandonado", "Abandonado"),
    ]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carrinhos",
        db_column="usuario_id",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="ativo")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carrinhos"
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"

    @classmethod
    def obter_carrinho_ativo(cls, usuario):
        carrinho, _ = cls.objects.get_or_create(
            usuario=usuario, status="ativo"
        )
        return carrinho

    def __str__(self):
        return f"Carrinho #{self.id} ({self.status}) — {self.usuario}"


class ItemCarrinho(models.Model):
    id = models.BigAutoField(primary_key=True)
    carrinho = models.ForeignKey(
        Carrinho,
        on_delete=models.CASCADE,
        related_name="itens",
        db_column="carrinho_id",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="itens_carrinho",
        db_column="produto_id",
    )
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    data_adicionado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "itens_carrinho"
        verbose_name = "Item do carrinho"
        verbose_name_plural = "Itens do carrinho"
        unique_together = [("carrinho", "produto")]

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"


class Pedido(models.Model):
    STATUS_CHOICES = [
        ("aguardando_pagamento", "Aguardando pagamento"),
        ("pagamento_aprovado", "Pagamento aprovado"),
        ("processamento", "Em processamento"),
        ("enviado", "Enviado"),
        ("entregue", "Entregue"),
        ("cancelado", "Cancelado"),
    ]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
        db_column="usuario_id",
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="vendas",
        db_column="vendedor_id",
    )
    endereco = models.ForeignKey(
        Endereco,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pedidos",
        db_column="endereco_id",
    )
    forma_pagamento = models.ForeignKey(
        FormaPagamento,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pedidos",
        db_column="forma_pagamento_id",
    )
    endereco_snapshot = models.CharField(max_length=500)
    forma_pagamento_snapshot = models.CharField(max_length=150)
    status_pedido = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default="aguardando_pagamento"
    )
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    valor_frete = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prazo_entrega_dias = models.PositiveSmallIntegerField(null=True, blank=True)
    codigo_rastreio = models.CharField(max_length=50, null=True, blank=True)
    data_envio = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    PROXIMO_STATUS_VENDEDOR = {
        "aguardando_pagamento": "pagamento_aprovado",
        "pagamento_aprovado": "processamento",
        "processamento": "enviado",
    }

    class Meta:
        db_table = "pedidos"
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-data_criacao"]

    @property
    def valor_produtos(self):
        return self.valor_total - self.valor_frete

    def __str__(self):
        return f"Pedido #{self.id} — {self.usuario}"


class ItemPedido(models.Model):
    id = models.BigAutoField(primary_key=True)
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.PROTECT,
        related_name="itens",
        db_column="pedido_id",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True,
        related_name="itens_pedido",
        db_column="produto_id",
    )
    nome_produto = models.CharField(max_length=150)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "itens_pedido"
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"

    def __str__(self):
        return f"{self.quantidade}x {self.nome_produto} (pedido #{self.pedido_id})"


class Contato(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("respondido", "Respondido"),
        ("arquivado", "Arquivado"),
    ]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensagens_contato",
        db_column="usuario_id",
    )
    nome = models.CharField(max_length=150)
    email = models.EmailField(max_length=254)
    assunto = models.CharField(max_length=150)
    mensagem = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contatos"
        verbose_name = "Mensagem de contato"
        verbose_name_plural = "Mensagens de contato"
        ordering = ["-data_envio"]

    def __str__(self):
        return f"{self.assunto} — {self.nome}"


class Avaliacao(models.Model):
    STATUS_CHOICES = [
        ("publicada", "Publicada"),
        ("oculta", "Oculta"),
        ("removida", "Removida"),
    ]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="avaliacoes",
        db_column="usuario_id",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="avaliacoes",
        db_column="produto_id",
    )
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="avaliacoes",
        db_column="pedido_id",
    )
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(null=True, blank=True)
    data_avaliacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="publicada")

    class Meta:
        db_table = "avaliacoes"
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"
        unique_together = [("usuario", "produto", "pedido")]

    def clean(self):
        from django.core.exceptions import ValidationError

        if not (1 <= self.nota <= 5):
            raise ValidationError({"nota": "A nota deve estar entre 1 e 5."})

        if self.pedido_id and self.produto_id:
            comprou = ItemPedido.objects.filter(
                pedido_id=self.pedido_id, produto_id=self.produto_id
            ).exists()
            if not comprou:
                raise ValidationError(
                    "Este produto não faz parte dos itens desse pedido."
                )
            if self.pedido.usuario_id != self.usuario_id:
                raise ValidationError("Este pedido não pertence a este usuário.")
            if self.pedido.status_pedido != "entregue":
                raise ValidationError(
                    "Só é possível avaliar produtos de pedidos já entregues."
                )

    def __str__(self):
        return f"{self.produto.nome} — nota {self.nota} ({self.usuario})"


class TabelaFrete(models.Model):

    REGIAO_CHOICES = [
        ("norte", "Norte"),
        ("nordeste", "Nordeste"),
        ("centro_oeste", "Centro-Oeste"),
        ("sudeste", "Sudeste"),
        ("sul", "Sul"),
    ]

    id = models.AutoField(primary_key=True)
    uf = models.CharField(max_length=2, unique=True)
    regiao = models.CharField(max_length=15, choices=REGIAO_CHOICES)
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    prazo_dias = models.PositiveSmallIntegerField()
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "tabela_frete"
        verbose_name = "Faixa de frete"
        verbose_name_plural = "Tabela de frete"
        ordering = ["regiao", "uf"]

    def __str__(self):
        return f"{self.uf} — R$ {self.valor} ({self.prazo_dias} dias)"


class PerguntaFrequente(models.Model):
    TEMA_CHOICES = [
        ("conta", "Conta e cadastro"),
        ("compras", "Compras e pagamento"),
        ("entrega", "Frete e entrega"),
        ("vendas", "Vendendo na contratempo"),
        ("seguranca", "Segurança e privacidade"),
    ]

    id = models.AutoField(primary_key=True)
    tema = models.CharField(max_length=15, choices=TEMA_CHOICES)
    pergunta = models.CharField(max_length=200)
    resposta = models.TextField()
    ordem = models.PositiveSmallIntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "perguntas_frequentes"
        verbose_name = "Pergunta frequente"
        verbose_name_plural = "Perguntas frequentes"
        ordering = ["tema", "ordem", "id"]

    def __str__(self):
        return self.pergunta


class PerguntaProduto(models.Model):
    STATUS_CHOICES = [
        ("publicada", "Publicada"),
        ("oculta", "Oculta"),
    ]

    id = models.BigAutoField(primary_key=True)
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="perguntas",
        db_column="produto_id",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perguntas_feitas",
        db_column="usuario_id",
    )
    pergunta = models.TextField(max_length=500)
    resposta = models.TextField(max_length=1000, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="publicada")
    data_pergunta = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "perguntas_produto"
        verbose_name = "Pergunta ao vendedor"
        verbose_name_plural = "Perguntas aos vendedores"
        ordering = ["-data_pergunta"]

    def __str__(self):
        return f"{self.produto.nome}: {self.pergunta[:50]}"


class Denuncia(models.Model):

    MOTIVO_CHOICES = [
        ("falsificado", "Produto falsificado ou pirata"),
        ("proibido", "Item proibido ou ilegal"),
        ("enganoso", "Descrição ou fotos enganosas"),
        ("golpe", "Suspeita de golpe"),
        ("ofensivo", "Conteúdo ofensivo"),
        ("outro", "Outro motivo"),
    ]
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("procedente", "Procedente (anúncio encerrado)"),
        ("improcedente", "Improcedente"),
    ]

    id = models.BigAutoField(primary_key=True)
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="denuncias",
        db_column="produto_id",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="denuncias_feitas",
        db_column="usuario_id",
    )
    motivo = models.CharField(max_length=15, choices=MOTIVO_CHOICES)
    descricao = models.TextField(max_length=1000, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pendente")
    data_denuncia = models.DateTimeField(auto_now_add=True)
    data_analise = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "denuncias"
        verbose_name = "Denúncia"
        verbose_name_plural = "Denúncias"
        ordering = ["-data_denuncia"]

    def __str__(self):
        return f"{self.get_motivo_display()} — {self.produto.nome}"
