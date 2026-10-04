"""
marketplace/estaticos.py

Arquivos estáticos (CSS, JS, imagens) com "impressão digital" no nome em
produção: o collectstatic gera, por exemplo, styles-retro.3f9a1c2b.css, e
o {% static %} passa a apontar para esse nome. Quando o arquivo muda, o
nome muda — e todo navegador baixa a versão nova, em vez de continuar
usando a cópia antiga guardada em cache (foi o que fez o aviso de cookies
aparecer sem estilo, no topo da página).

Diferença para o ManifestStaticFilesStorage padrão do Django: arquivos
citados no CSS que não existem (a fonte Adult Swim é opcional, ver
static/fonts/LEIA-ME.txt) não travam o collectstatic nem derrubam a página;
ficam com o nome original.

Ativado em settings.py só com DEBUG desligado (no PC tudo segue igual).
"""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class EstaticosComVersao(ManifestStaticFilesStorage):
    manifest_strict = False  # arquivo fora do manifesto: usa o nome original em vez de dar erro 500

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:  # arquivo não existe (ex.: fonte opcional ainda não colocada)
            return name
