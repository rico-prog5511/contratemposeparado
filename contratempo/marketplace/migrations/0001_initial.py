import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=80, unique=True)),
                ('slug', models.SlugField(max_length=90, unique=True)),
                ('descricao', models.CharField(blank=True, max_length=255, null=True)),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Categoria',
                'verbose_name_plural': 'Categorias',
                'db_table': 'categorias',
            },
        ),
        migrations.CreateModel(
            name='Franquia',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=110, unique=True)),
                ('descricao', models.CharField(blank=True, max_length=255, null=True)),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Franquia',
                'verbose_name_plural': 'Franquias',
                'db_table': 'franquias',
            },
        ),
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nome_completo', models.CharField(max_length=150)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('password', models.CharField(db_column='senha', max_length=128)),
                ('data_nascimento', models.DateField(blank=True, null=True)),
                ('telefone', models.CharField(blank=True, max_length=20, null=True)),
                ('avatar', models.CharField(blank=True, max_length=255, null=True)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('status_conta', models.CharField(choices=[('ativo', 'Ativo'), ('inativo', 'Inativo'), ('suspenso', 'Suspenso')], default='ativo', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'Usuário',
                'verbose_name_plural': 'Usuários',
                'db_table': 'usuarios',
            },
        ),
        migrations.CreateModel(
            name='Carrinho',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('ativo', 'Ativo'), ('finalizado', 'Finalizado'), ('abandonado', 'Abandonado')], default='ativo', max_length=12)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('usuario', models.ForeignKey(db_column='usuario_id', on_delete=django.db.models.deletion.CASCADE, related_name='carrinhos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Carrinho',
                'verbose_name_plural': 'Carrinhos',
                'db_table': 'carrinhos',
            },
        ),
        migrations.CreateModel(
            name='Contato',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=150)),
                ('email', models.EmailField(max_length=254)),
                ('assunto', models.CharField(max_length=150)),
                ('mensagem', models.TextField()),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('respondido', 'Respondido'), ('arquivado', 'Arquivado')], default='pendente', max_length=10)),
                ('data_envio', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(blank=True, db_column='usuario_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mensagens_contato', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Mensagem de contato',
                'verbose_name_plural': 'Mensagens de contato',
                'db_table': 'contatos',
                'ordering': ['-data_envio'],
            },
        ),
        migrations.CreateModel(
            name='Endereco',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nome_endereco', models.CharField(max_length=100)),
                ('cep', models.CharField(max_length=10)),
                ('logradouro', models.CharField(max_length=150)),
                ('numero', models.CharField(max_length=20)),
                ('complemento', models.CharField(blank=True, max_length=100, null=True)),
                ('bairro', models.CharField(max_length=100)),
                ('cidade', models.CharField(max_length=100)),
                ('estado', models.CharField(max_length=2)),
                ('pais', models.CharField(default='Brasil', max_length=60)),
                ('endereco_principal', models.BooleanField(default=False)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(db_column='usuario_id', on_delete=django.db.models.deletion.CASCADE, related_name='enderecos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Endereço',
                'verbose_name_plural': 'Endereços',
                'db_table': 'enderecos',
            },
        ),
        migrations.CreateModel(
            name='FormaPagamento',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('tipo', models.CharField(choices=[('cartao_credito', 'Cartão de crédito'), ('cartao_debito', 'Cartão de débito'), ('pix', 'PIX'), ('boleto', 'Boleto'), ('outro', 'Outro')], max_length=20)),
                ('apelido', models.CharField(blank=True, max_length=60, null=True)),
                ('ultimos_digitos', models.CharField(blank=True, max_length=4, null=True)),
                ('bandeira', models.CharField(blank=True, max_length=30, null=True)),
                ('token_externo', models.CharField(blank=True, max_length=255, null=True)),
                ('principal', models.BooleanField(default=False)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(db_column='usuario_id', on_delete=django.db.models.deletion.CASCADE, related_name='formas_pagamento', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Forma de pagamento',
                'verbose_name_plural': 'Formas de pagamento',
                'db_table': 'formas_pagamento',
            },
        ),
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('endereco_snapshot', models.CharField(max_length=500)),
                ('forma_pagamento_snapshot', models.CharField(max_length=150)),
                ('status_pedido', models.CharField(choices=[('aguardando_pagamento', 'Aguardando pagamento'), ('pagamento_aprovado', 'Pagamento aprovado'), ('processamento', 'Em processamento'), ('enviado', 'Enviado'), ('entregue', 'Entregue'), ('cancelado', 'Cancelado')], default='aguardando_pagamento', max_length=25)),
                ('valor_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('endereco', models.ForeignKey(db_column='endereco_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos', to='marketplace.endereco')),
                ('forma_pagamento', models.ForeignKey(db_column='forma_pagamento_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos', to='marketplace.formapagamento')),
                ('usuario', models.ForeignKey(db_column='usuario_id', on_delete=django.db.models.deletion.PROTECT, related_name='pedidos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pedido',
                'verbose_name_plural': 'Pedidos',
                'db_table': 'pedidos',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='Produto',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=150)),
                ('descricao', models.TextField()),
                ('preco', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quantidade_disponivel', models.PositiveIntegerField(default=0)),
                ('condicao', models.CharField(choices=[('novo', 'Novo'), ('usado', 'Usado'), ('semi_novo', 'Semi-novo')], default='usado', max_length=10)),
                ('marca', models.CharField(blank=True, max_length=80, null=True)),
                ('ano', models.SmallIntegerField(blank=True, null=True)),
                ('sku', models.CharField(blank=True, max_length=50, null=True, unique=True)),
                ('status_anuncio', models.CharField(choices=[('ativo', 'Ativo'), ('pausado', 'Pausado'), ('vendido', 'Vendido'), ('encerrado', 'Encerrado')], default='ativo', max_length=10)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('categoria', models.ForeignKey(db_column='categoria_id', on_delete=django.db.models.deletion.PROTECT, related_name='produtos', to='marketplace.categoria')),
                ('franquia', models.ForeignKey(blank=True, db_column='franquia_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='produtos', to='marketplace.franquia')),
                ('vendedor', models.ForeignKey(db_column='vendedor_id', on_delete=django.db.models.deletion.PROTECT, related_name='produtos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Produto',
                'verbose_name_plural': 'Produtos',
                'db_table': 'produtos',
            },
        ),
        migrations.CreateModel(
            name='ItemPedido',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nome_produto', models.CharField(max_length=150)),
                ('preco_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quantidade', models.PositiveIntegerField()),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=10)),
                ('pedido', models.ForeignKey(db_column='pedido_id', on_delete=django.db.models.deletion.PROTECT, related_name='itens', to='marketplace.pedido')),
                ('produto', models.ForeignKey(db_column='produto_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_pedido', to='marketplace.produto')),
            ],
            options={
                'verbose_name': 'Item do pedido',
                'verbose_name_plural': 'Itens do pedido',
                'db_table': 'itens_pedido',
            },
        ),
        migrations.CreateModel(
            name='ProdutoImagem',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('url_imagem', models.CharField(max_length=255)),
                ('principal', models.BooleanField(default=False)),
                ('ordem_exibicao', models.SmallIntegerField(default=0)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('produto', models.ForeignKey(db_column='produto_id', on_delete=django.db.models.deletion.CASCADE, related_name='imagens', to='marketplace.produto')),
            ],
            options={
                'verbose_name': 'Imagem do produto',
                'verbose_name_plural': 'Imagens do produto',
                'db_table': 'produto_imagens',
                'ordering': ['ordem_exibicao'],
            },
        ),
        migrations.CreateModel(
            name='ItemCarrinho',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('quantidade', models.PositiveIntegerField(default=1)),
                ('preco_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('data_adicionado', models.DateTimeField(auto_now_add=True)),
                ('carrinho', models.ForeignKey(db_column='carrinho_id', on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='marketplace.carrinho')),
                ('produto', models.ForeignKey(db_column='produto_id', on_delete=django.db.models.deletion.CASCADE, related_name='itens_carrinho', to='marketplace.produto')),
            ],
            options={
                'verbose_name': 'Item do carrinho',
                'verbose_name_plural': 'Itens do carrinho',
                'db_table': 'itens_carrinho',
                'unique_together': {('carrinho', 'produto')},
            },
        ),
        migrations.CreateModel(
            name='Avaliacao',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nota', models.PositiveSmallIntegerField()),
                ('comentario', models.TextField(blank=True, null=True)),
                ('data_avaliacao', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('publicada', 'Publicada'), ('oculta', 'Oculta'), ('removida', 'Removida')], default='publicada', max_length=10)),
                ('usuario', models.ForeignKey(db_column='usuario_id', on_delete=django.db.models.deletion.CASCADE, related_name='avaliacoes', to=settings.AUTH_USER_MODEL)),
                ('pedido', models.ForeignKey(db_column='pedido_id', on_delete=django.db.models.deletion.CASCADE, related_name='avaliacoes', to='marketplace.pedido')),
                ('produto', models.ForeignKey(db_column='produto_id', on_delete=django.db.models.deletion.CASCADE, related_name='avaliacoes', to='marketplace.produto')),
            ],
            options={
                'verbose_name': 'Avaliação',
                'verbose_name_plural': 'Avaliações',
                'db_table': 'avaliacoes',
                'unique_together': {('usuario', 'produto', 'pedido')},
            },
        ),
    ]
