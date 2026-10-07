import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PerguntaFrequente',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('tema', models.CharField(choices=[('conta', 'Conta e cadastro'), ('compras', 'Compras e pagamento'), ('entrega', 'Frete e entrega'), ('vendas', 'Vendendo na contratempo'), ('seguranca', 'Segurança e privacidade')], max_length=15)),
                ('pergunta', models.CharField(max_length=200)),
                ('resposta', models.TextField()),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Pergunta frequente',
                'verbose_name_plural': 'Perguntas frequentes',
                'db_table': 'perguntas_frequentes',
                'ordering': ['tema', 'ordem', 'id'],
            },
        ),
        migrations.CreateModel(
            name='TabelaFrete',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('uf', models.CharField(max_length=2, unique=True)),
                ('regiao', models.CharField(choices=[('norte', 'Norte'), ('nordeste', 'Nordeste'), ('centro_oeste', 'Centro-Oeste'), ('sudeste', 'Sudeste'), ('sul', 'Sul')], max_length=15)),
                ('valor', models.DecimalField(decimal_places=2, max_digits=8)),
                ('prazo_dias', models.PositiveSmallIntegerField()),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Faixa de frete',
                'verbose_name_plural': 'Tabela de frete',
                'db_table': 'tabela_frete',
                'ordering': ['regiao', 'uf'],
            },
        ),
        migrations.AddField(
            model_name='pedido',
            name='codigo_rastreio',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='data_envio',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='prazo_entrega_dias',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='valor_frete',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='pedido',
            name='vendedor',
            field=models.ForeignKey(db_column='vendedor_id', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='vendas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='usuario',
            name='email_confirmado',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='PerguntaProduto',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('pergunta', models.TextField(max_length=500)),
                ('resposta', models.TextField(blank=True, max_length=1000, null=True)),
                ('status', models.CharField(choices=[('publicada', 'Publicada'), ('oculta', 'Oculta')], default='publicada', max_length=10)),
                ('data_pergunta', models.DateTimeField(auto_now_add=True)),
                ('data_resposta', models.DateTimeField(blank=True, null=True)),
                ('produto', models.ForeignKey(db_column='produto_id', on_delete=django.db.models.deletion.CASCADE, related_name='perguntas', to='marketplace.produto')),
                ('usuario', models.ForeignKey(db_column='usuario_id', on_delete=django.db.models.deletion.CASCADE, related_name='perguntas_feitas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pergunta ao vendedor',
                'verbose_name_plural': 'Perguntas aos vendedores',
                'db_table': 'perguntas_produto',
                'ordering': ['-data_pergunta'],
            },
        ),
    ]
