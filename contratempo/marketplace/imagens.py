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
    copia = imagem.copy()
    copia.thumbnail((lado_max, lado_max), Image.LANCZOS)
    saida = io.BytesIO()
    copia.save(saida, "WEBP", quality=QUALIDADE, method=6)
    return saida.getvalue()


def abrir(arquivo):
    imagem = Image.open(arquivo)
    imagem = ImageOps.exif_transpose(imagem)
    if imagem.mode in ("P", "LA") or (imagem.mode == "RGBA" and imagem.getextrema()[3][0] < 255):
        return imagem.convert("RGBA")
    return imagem.convert("RGB")


def caminho_da_url(url):
    prefixo = "/" + settings.MEDIA_URL.strip("/") + "/"
    url = url or ""
    return url[len(prefixo):] if url.startswith(prefixo) else ""


def salvar_foto_produto(arquivo, pasta):
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
    caminho = caminho_da_url(url)
    if not caminho.endswith(".webp") or caminho.endswith(SUFIXO_MINI):
        return url
    mini = caminho[: -len(".webp")] + SUFIXO_MINI
    return default_storage.url(mini) if default_storage.exists(mini) else url
