"""
python manage.py otimizar_banner

Gera, a partir da foto do banner (static/img/banner/banner-1.png/.jpg/
.jpeg/.webp), duas versões leves em WebP:

    banner-1-1920.webp   telas grandes   (~200 KB em vez de ~3 MB)
    banner-1-1280.webp   tablet / notebook pequeno (~100 KB)
    banner-1-800.webp    celular         (~45 KB)

A home usa essas versões quando existem e estão mais novas que a foto
original (views._foto_banner); senão, usa a original. O atualizar.sh roda
este comando antes do collectstatic, então no PythonAnywhere é automático.
No PC, rode-o depois de trocar a foto (ou o site usa a original, mais
pesada, até você rodar).

As versões geradas não vão para o Git (.gitignore): cada máquina gera as
suas a partir da foto original.
"""

from pathlib import Path

from django.core.management.base import BaseCommand
from PIL import Image

PASTA = Path(__file__).resolve().parents[2] / "static" / "img" / "banner"
ORIGINAIS = ("banner-1.webp", "banner-1.jpg", "banner-1.jpeg", "banner-1.png")
VERSOES = ((1920, 80), (1280, 78), (800, 75))  # (largura máxima, qualidade WebP)


class Command(BaseCommand):
    help = "Gera as versões WebP leves da foto do banner da home."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true", help="Gera de novo mesmo se já estiverem atualizadas.")

    def handle(self, *args, forcar=False, **opcoes):
        original = next((PASTA / nome for nome in ORIGINAIS if (PASTA / nome).exists()), None)
        if original is None:
            self.stdout.write("Sem foto do banner (banner-1.*): nada a fazer.")
            return

        foto = None
        for largura, qualidade in VERSOES:
            destino = PASTA / f"banner-1-{largura}.webp"
            if not forcar and destino.exists() and destino.stat().st_mtime >= original.stat().st_mtime:
                self.stdout.write(f"{destino.name}: já está atualizada.")
                continue
            if foto is None:
                foto = Image.open(original).convert("RGB")
            imagem = foto
            if foto.width > largura:
                imagem = foto.resize((largura, round(foto.height * largura / foto.width)), Image.LANCZOS)
            imagem.save(destino, "WEBP", quality=qualidade, method=6)
            self.stdout.write(self.style.SUCCESS(
                f"{destino.name}: {imagem.width}x{imagem.height}, {destino.stat().st_size // 1024} KB "
                f"(original {original.name}: {original.stat().st_size // 1024} KB)"
            ))
