"""
marketplace/models.py

Models do Contratempo mapeados para as tabelas já existentes em
contratempo_db.sql. Todos usam managed = True: o Django é responsável
por futuras migrations, e a tabela inicial criada pelo SQL é "adotada"
via `migrate --fake-initial` (ver seção H do guia).

Não existe Model de Favorito — a funcionalidade foi removida do projeto.
"""

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


# =====================================================================
# USUÁRIO PERSONALIZADO
# =====================================================================

class UsuarioManager(BaseUserManager):
    """
    Manager customizado: usa e-mail como identificador de login e
    normaliza (lowercase) o e-mail antes de salvar, para manter
    consistência com a collation case-insensitive do MySQL.

    IMPORTANTE: o parâmetro precisa se chamar exatamente "password"
    (não "senha"). O comando `createsuperuser` do Django sempre
    chama create_superuser(**user_data) passando a senha digitada
    com a chave "password" — se o parâmetro tivesse outro nome, a
    senha real cairia em **extra_fields (e seria sobrescrita por
    set_password(None), gerando uma senha inutilizável). O nome da
    COLUNA no banco continua sendo "senha" (mapeado via db_column
    no campo `password` do Model abaixo); só o parâmetro do manager
    precisa seguir a convenção do Django.
    """

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
    """
    Mapeia a tabela `usuarios`. Substitui completamente o User padrão
    do Django (AUTH_USER_MODEL = "marketplace.Usuario").
    """

    STATUS_CONTA_CHOICES = [
        ("ativo", "Ativo"),
        ("inativo", "Inativo"),
        ("suspenso", "Suspenso"),
    ]

    id = models.BigAutoField(primary_key=True)
    nome_completo = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, unique=True)
    # "password" é o nome esperado internamente pelo Django
    # (set_password/check_password); mapeamos para a coluna "senha".
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
    # is_superuser já é fornecido pelo PermissionsMixin
    # Contas criadas pelo site começam com False até o usuário clicar no
    # link enviado por e-mail. O default True mantém liberados os
    # usuários antigos e os criados por createsuperuser/admin.
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
        """Soft-delete: nunca excluir fisicamente um usuário com produtos."""
        self.is_active = False
        self.status_conta = "inativo"
        self.save(update_fields=["is_active", "status_conta"])


# =====================================================================
# ENDEREÇOS E FORMAS DE PAGAMENTO
# =====================================================================

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
        ("pix", "PIX"),
        ("boleto", "Boleto"),
        ("outro", "Outro"),
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
    bandeira = models.CharField(max_length=30, null=True, blank=True)
    token_externo = models.CharField(max_length=255, null=True, blank=True)
    principal = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "formas_pagamento"
        verbose_name = "Forma de pagamento"
        verbose_name_plural = "Formas de pagamento"

    def __str__(self):
        return self.apelido or f"{self.get_tipo_display()} ****{self.ultimos_digitos or ''}"


# =====================================================================
# CATEGORIAS E FRANQUIAS
# =====================================================================

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


# =====================================================================
# PRODUTOS
# =====================================================================

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
        on_delete=models.PROTECT,  # nunca apagar produtos junto do usuário
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
    # Em produção, trocar por models.ImageField(upload_to=...) e
    # armazenar o campo .name aqui; mantido como CharField para
    # compatibilidade direta com a coluna VARCHAR já existente.
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
        # Garante uma única imagem principal por produto.
        if self.principal:
            ProdutoImagem.objects.filter(
                produto_id=self.produto_id, principal=True
            ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Imagem de {self.produto.nome} (#{self.ordem_exibicao})"


# =====================================================================
# CARRINHO
# =====================================================================

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
    # A coluna gerada `usuario_carrinho_ativo` existe no banco para
    # garantir (via UNIQUE) um único carrinho ativo por usuário, mas
    # não precisa ser exposta como campo do Model.

    class Meta:
        db_table = "carrinhos"
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"

    @classmethod
    def obter_carrinho_ativo(cls, usuario):
        """Ponto único para obter/criar o carrinho ativo de um usuário."""
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


# =====================================================================
# PEDIDOS
# =====================================================================

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
        on_delete=models.PROTECT,  # histórico de vendas nunca é apagado
        related_name="pedidos",
        db_column="usuario_id",
    )
    # O checkout gera UM pedido por vendedor: cada vendedor envia, cobra
    # frete e atualiza o status do seu pedido de forma independente.
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,  # pedidos antigos, anteriores à divisão por vendedor
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
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)  # produtos + frete
    valor_frete = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prazo_entrega_dias = models.PositiveSmallIntegerField(null=True, blank=True)
    codigo_rastreio = models.CharField(max_length=50, null=True, blank=True)
    data_envio = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # Etapas que o VENDEDOR pode aplicar, a partir de cada status.
    # "entregue" é confirmado pelo comprador (ou pelo admin).
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
        on_delete=models.PROTECT,  # nunca apagar item junto do pedido
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


# =====================================================================
# CONTATO
# =====================================================================

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


# =====================================================================
# AVALIAÇÕES
# =====================================================================

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
        """
        Regra de negócio que o banco NÃO garante sozinho: só quem
        realmente comprou o produto (nesse pedido, já entregue) pode
        avaliá-lo. Chamado por full_clean() no ModelForm/Admin/serializer.
        """
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

# =====================================================================
# FRETE
# =====================================================================

class TabelaFrete(models.Model):
    """
    Valor e prazo de entrega por UF de destino, editáveis no /admin/.
    O checkout cobra UM frete por vendedor (cada vendedor envia seu
    pacote). Os valores iniciais vêm da migration 0003 e devem ser
    ajustados à realidade do negócio.
    """

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


# =====================================================================
# DÚVIDAS FREQUENTES
# =====================================================================

class PerguntaFrequente(models.Model):
    TEMA_CHOICES = [
        ("conta", "Conta e cadastro"),
        ("compras", "Compras e pagamento"),
        ("entrega", "Frete e entrega"),
        ("vendas", "Vendendo na Contratempo"),
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


# =====================================================================
# PERGUNTAS AO VENDEDOR
# =====================================================================

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


# =====================================================================
# DENÚNCIAS DE ANÚNCIOS
# =====================================================================

class Denuncia(models.Model):
    """
    Denúncia de um anúncio feita por um usuário. A equipe analisa no
    /admin/ (Denúncias): "procedente" encerra o anúncio, "improcedente"
    só arquiva. O vendedor não fica sabendo quem denunciou.
    """

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
