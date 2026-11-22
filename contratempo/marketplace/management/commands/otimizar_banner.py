import re
from pathlib import Path

from django.core.management.base import BaseCommand
from PIL import Image

PASTA = Path(__file__).resolve().parents[2] / "static" / "img" / "banner"
EXTENSOES = ("webp", "jpg", "jpeg", "png")
ORIGINAL = re.compile(r"^banner-(\d+)\.(webp|jpg|jpeg|png)$")
VERSOES = ((1920, 80), (1280, 78), (800, 75))


def originais():
    por_numero = {}
    for arquivo in PASTA.iterdir():
        achado = ORIGINAL.match(arquivo.name)
        if achado:
            numero, extensao = int(achado.group(1)), achado.group(2)
            atual = por_numero.get(numero)
            if atual is None or EXTENSOES.index(extensao) < EXTENSOES.index(atual.suffix[1:]):
                por_numero[numero] = arquivo
    return [por_numero[n] for n in sorted(por_numero)]


class Command(BaseCommand):
    help = "Gera as versões WebP leves das imagens do banner da home."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true", help="Gera de novo mesmo se já estiverem atualizadas.")

    def handle(self, *args, forcar=False, **opcoes):
        lista = originais()
        if not lista:
            self.stdout.write("Sem imagens do banner (banner-1.*, banner-2.*...): nada a fazer.")
            return

        for original in lista:
            foto = None
            for largura, qualidade in VERSOES:
                destino = PASTA / f"{original.stem}-{largura}.webp"
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
