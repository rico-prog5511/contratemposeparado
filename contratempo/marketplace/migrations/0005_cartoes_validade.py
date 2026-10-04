"""
Formas de pagamento passam a ser só cartões (com validade).

PIX e boleto agora são escolhidos direto no checkout, então as formas
"pix", "boleto" e "outro" já salvas são apagadas. Pedidos antigos não
mudam: guardam o texto em forma_pagamento_snapshot e a ligação vira NULL
(on_delete=SET_NULL). Quem ficou sem cartão principal tem o mais antigo
promovido.

Equivale a banco/atualizacao_v4.sql (use um OU outro).
"""

from django.db import migrations, models

TIPOS_CARTAO = ("cartao_credito", "cartao_debito")


def so_cartoes(apps, schema_editor):
    FormaPagamento = apps.get_model("marketplace", "FormaPagamento")
    FormaPagamento.objects.exclude(tipo__in=TIPOS_CARTAO).delete()

    sem_principal = (
        FormaPagamento.objects.values_list("usuario_id", flat=True).distinct()
        .exclude(usuario_id__in=FormaPagamento.objects.filter(principal=True).values("usuario_id"))
    )
    for usuario_id in list(sem_principal):
        mais_antigo = FormaPagamento.objects.filter(usuario_id=usuario_id).order_by("data_cadastro").first()
        mais_antigo.principal = True
        mais_antigo.save(update_fields=["principal"])


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0004_denuncias'),
    ]

    operations = [
        migrations.RunPython(so_cartoes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='formapagamento',
            name='tipo',
            field=models.CharField(choices=[('cartao_credito', 'Cartão de crédito'), ('cartao_debito', 'Cartão de débito')], max_length=20),
        ),
        migrations.AlterField(
            model_name='formapagamento',
            name='bandeira',
            field=models.CharField(blank=True, choices=[('Visa', 'Visa'), ('Mastercard', 'Mastercard'), ('Elo', 'Elo'), ('American Express', 'American Express'), ('Hipercard', 'Hipercard')], max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='formapagamento',
            name='validade_mes',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='formapagamento',
            name='validade_ano',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
