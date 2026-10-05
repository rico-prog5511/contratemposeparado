"""
python manage.py otimizar_fotos [--simular]

Converte as fotos enviadas ANTES do tratamento automático (marketplace/
imagens.py): reduz, salva em WebP, cria a miniatura dos produtos e apaga
os dados escondidos (GPS etc.). Atualiza a URL no banco e apaga o
arquivo original pesado (só se nada mais o usar).

- Fotos já tratadas são puladas: pode rodar quantas vezes quiser.
- --simular mostra o que seria feito, sem mexer em nada.
- O atualizar.sh e o rodar.bat já rodam este comando.
"""

import os

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from marketplace.imagens import SUFIXO_MINI, SUFIXO_PERFIL, caminho_da_url, salvar_foto_perfil, salvar_foto_produto
from marketplace.models import ProdutoImagem, Usuario


def _ja_tratada_produto(caminho):
    return caminho.endswith(".webp") and default_storage.exists(caminho[: -len(".webp")] + SUFIXO_MINI)


class Command(BaseCommand):
    help = "Converte as fotos antigas de produtos e de perfil para o formato leve (WebP, sem GPS)."

    def add_arguments(self, parser):
        parser.add_argument("--simular", action="store_true", help="Só mostra o que seria convertido.")

    def handle(self, *args, simular=False, **opcoes):
        self.simular = simular
        self.antes = self.depois = 0
        self.convertidas = self.erros = 0

        # Agrupa por URL: a mesma foto pode estar em mais de um registro.
        fotos = {}
        for imagem in ProdutoImagem.objects.only("id", "url_imagem"):
            fotos.setdefault(imagem.url_imagem, []).append(imagem.id)
        for url, ids in fotos.items():
            caminho = caminho_da_url(url)
            if caminho and not _ja_tratada_produto(caminho):
                self._converter(url, caminho, salvar_foto_produto, lambda nova, ids=ids:
                                ProdutoImagem.objects.filter(id__in=ids).update(url_imagem=nova))

        avatares = {}
        for usuario in Usuario.objects.exclude(avatar__isnull=True).exclude(avatar="").only("id", "avatar"):
            avatares.setdefault(usuario.avatar, []).append(usuario.id)
        for url, ids in avatares.items():
            caminho = caminho_da_url(url)
            if caminho and not caminho.endswith(SUFIXO_PERFIL):
                self._converter(url, caminho, salvar_foto_perfil,
                                lambda nova, ids=ids: Usuario.objects.filter(id__in=ids).update(avatar=nova))

        if self.convertidas == 0 and self.erros == 0:
            self.stdout.write("Nenhuma foto para converter: todas já estão no formato leve.")
            return
        verbo = "Seriam convertidas" if simular else "Convertidas"
        resumo = f"{verbo}: {self.convertidas} foto(s), {self.antes // 1024} KB"
        if not simular:
            resumo += f" -> {self.depois // 1024} KB"
        self.stdout.write(self.style.SUCCESS(resumo))
        if self.erros:
            self.stdout.write(self.style.WARNING(f"{self.erros} foto(s) não puderam ser convertidas (veja acima)."))

    def _converter(self, url, caminho, salvar, atualizar_banco):
        if not default_storage.exists(caminho):
            self.stdout.write(self.style.WARNING(f"  arquivo não encontrado, pulei: {caminho}"))
            return
        tamanho = default_storage.size(caminho)
        if self.simular:
            self.stdout.write(f"  {caminho} ({tamanho // 1024} KB)")
            self.antes += tamanho
            self.convertidas += 1
            return
        try:
            with default_storage.open(caminho, "rb") as arquivo:
                nova = salvar(arquivo, os.path.dirname(caminho))
            with transaction.atomic():
                atualizar_banco(nova)
        except Exception as erro:  # foto corrompida etc.: segue com as outras
            self.erros += 1
            self.stdout.write(self.style.ERROR(f"  não consegui converter {caminho}: {type(erro).__name__}: {erro}"))
            return
        novo_caminho = caminho_da_url(nova)
        novo_tamanho = default_storage.size(novo_caminho)
        mini = novo_caminho[: -len(".webp")] + SUFIXO_MINI
        novo_tamanho_mini = default_storage.size(mini) if default_storage.exists(mini) else 0
        # Apaga o original só se nenhum registro ainda aponta para ele.
        ainda_usado = ProdutoImagem.objects.filter(url_imagem=url).exists() or Usuario.objects.filter(avatar=url).exists()
        if not ainda_usado and caminho != novo_caminho:
            default_storage.delete(caminho)
        self.antes += tamanho
        self.depois += novo_tamanho
        self.convertidas += 1
        extra = f" + miniatura {novo_tamanho_mini // 1024} KB" if novo_tamanho_mini else ""
        self.stdout.write(f"  {caminho} ({tamanho // 1024} KB) -> {os.path.basename(novo_caminho)} ({novo_tamanho // 1024} KB{extra})")
