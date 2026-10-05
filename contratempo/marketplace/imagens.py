"""
marketplace/imagens.py

Tratamento das fotos enviadas (produtos e perfil), feito no momento do
envio:

- gira a foto do jeito certo (fotos de celular guardam a orientação à parte);
- reduz o tamanho (produto: até 1600 px; perfil: até 400 px);
- salva em WebP, bem mais leve que JPG/PNG;
- APAGA os dados escondidos da foto (EXIF), que podem incluir a localização
  GPS de onde ela foi tirada — ou seja, a casa do vendedor;
- produtos ganham também uma miniatura de 600 px para cards e listas.

Nomes dos arquivos (é assim que se sabe se uma foto já foi tratada):
    produtos/<id>/<código>.webp        foto principal (até 1600 px)
    produtos/<id>/<código>-mini.webp   miniatura (até 600 px)
    avatares/<código>-perfil.webp      foto de perfil (até 400 px)

Nada muda no banco: ProdutoImagem.url_imagem e Usuario.avatar continuam
guardando a URL da foto. Fotos antigas são convertidas por
`python manage.py otimizar_fotos` (o atualizar.sh já roda).
"""

import io
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps

PRODUTO_MAX = 1600
MINIATURA_MAX = 600
PERFIL_MAX = 400
QUALIDADE = 80
SUFIXO_MINI = "-mini.webp"
SUFIXO_PERFIL = "-perfil.webp"


def _webp(imagem, lado_max):
    """Imagem do Pillow -> bytes WebP com o maior lado <= lado_max, sem EXIF."""
    copia = imagem.copy()
    copia.thumbnail((lado_max, lado_max), Image.LANCZOS)  # só reduz, nunca aumenta
    saida = io.BytesIO()
    # Sem exif=... o Pillow não grava os metadados: GPS, modelo do celular etc. somem.
    copia.save(saida, "WEBP", quality=QUALIDADE, method=6)
    return saida.getvalue()


def abrir(arquivo):
    """Abre a foto já girada do jeito certo e num modo de cor que o WebP aceita."""
    imagem = Image.open(arquivo)
    imagem = ImageOps.exif_transpose(imagem)  # aplica a orientação gravada pelo celular
    if imagem.mode in ("P", "LA") or (imagem.mode == "RGBA" and imagem.getextrema()[3][0] < 255):
        return imagem.convert("RGBA")  # mantém a transparência de PNGs
    return imagem.convert("RGB")


def caminho_da_url(url):
    """'/media/produtos/1/x.webp' -> 'produtos/1/x.webp' (caminho no armazenamento)."""
    prefixo = "/" + settings.MEDIA_URL.strip("/") + "/"
    url = url or ""
    return url[len(prefixo):] if url.startswith(prefixo) else ""


def salvar_foto_produto(arquivo, pasta):
    """Salva a foto do produto (principal + miniatura) e devolve a URL da principal."""
    imagem = abrir(arquivo)
    codigo = uuid.uuid4().hex
    principal = default_storage.save(f"{pasta}/{codigo}.webp", ContentFile(_webp(imagem, PRODUTO_MAX)))
    default_storage.save(principal[: -len(".webp")] + SUFIXO_MINI, ContentFile(_webp(imagem, MINIATURA_MAX)))
    return default_storage.url(principal)


def salvar_foto_perfil(arquivo, pasta="avatares"):
    imagem = abrir(arquivo)
    nome = default_storage.save(f"{pasta}/{uuid.uuid4().hex}{SUFIXO_PERFIL}", ContentFile(_webp(imagem, PERFIL_MAX)))
    return default_storage.url(nome)


def url_miniatura(url):
    """URL da miniatura de uma foto de produto; se ela não existir (foto antiga), a própria foto."""
    caminho = caminho_da_url(url)
    if not caminho.endswith(".webp") or caminho.endswith(SUFIXO_MINI):
        return url
    mini = caminho[: -len(".webp")] + SUFIXO_MINI
    return default_storage.url(mini) if default_storage.exists(mini) else url
