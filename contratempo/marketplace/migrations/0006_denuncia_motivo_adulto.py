from django.db import migrations, models


def motivo_como_texto_no_mysql(apps, schema_editor):
    if schema_editor.connection.vendor == "mysql":
        schema_editor.execute("ALTER TABLE `denuncias` MODIFY `motivo` varchar(15) NOT NULL")


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0005_cartoes_validade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='denuncia',
            name='motivo',
            field=models.CharField(choices=[('falsificado', 'Produto falsificado ou pirata'), ('proibido', 'Item proibido ou ilegal'), ('adulto', 'Conteúdo adulto (+18)'), ('enganoso', 'Descrição ou fotos enganosas'), ('golpe', 'Suspeita de golpe'), ('ofensivo', 'Conteúdo ofensivo'), ('outro', 'Outro motivo')], max_length=15),
        ),
        migrations.RunPython(motivo_como_texto_no_mysql, migrations.RunPython.noop),
    ]
