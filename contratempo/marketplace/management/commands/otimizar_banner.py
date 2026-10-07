from pathlib import Path

from django.core.management.base import BaseCommand
from PIL import Image

PASTA = Path(__file__).resolve().parents[2] / "static" / "img" / "banner"
ORIGINAIS = ("banner-1.webp", "banner-1.jpg", "banner-1.jpeg", "banner-1.png")
VERSOES = ((1920, 80), (1280, 78), (800, 75))


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
