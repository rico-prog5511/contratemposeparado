import unicodedata

from django.db.models import CharField, Func, Q

CAMPOS_BUSCA = ["nome", "descricao", "marca", "franquia__nome", "categoria__nome"]


def normalizar(texto):
    decomposto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


class SemAcento(Func):

    function = "LOWER"
    output_field = CharField()

    def as_sqlite(self, compiler, connection, **extra):
        return super().as_sql(compiler, connection, function="SEM_ACENTO", **extra)


def registrar_funcao_sqlite(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        connection.connection.create_function(
            "SEM_ACENTO", 1, lambda valor: normalizar(valor) if valor is not None else None, deterministic=True
        )


def palavras(termo):
    return [p for p in normalizar(termo).split() if p]


def filtrar(qs, termo, campos=CAMPOS_BUSCA):
    lista = palavras(termo)
    if not lista:
        return qs
    anotacoes = {f"_busca_{i}": SemAcento(campo) for i, campo in enumerate(campos)}
    qs = qs.annotate(**anotacoes)
    for palavra in lista:
        condicao = Q()
        for apelido in anotacoes:
            condicao |= Q(**{f"{apelido}__icontains": palavra})
        qs = qs.filter(condicao)
    return qs
