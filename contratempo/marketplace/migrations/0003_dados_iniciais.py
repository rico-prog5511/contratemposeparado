from django.db import migrations

REGIOES = {
    "sudeste": (["SP", "RJ", "MG", "ES"], "19.90", 5),
    "sul": (["PR", "SC", "RS"], "24.90", 7),
    "centro_oeste": (["DF", "GO", "MT", "MS"], "29.90", 8),
    "nordeste": (["BA", "SE", "AL", "PE", "PB", "RN", "CE", "PI", "MA"], "34.90", 10),
    "norte": (["PA", "AP", "AM", "RR", "AC", "RO", "TO"], "39.90", 12),
}

FAQ = [
    ("conta", "Como crio minha conta?",
     "Clique no ícone de pessoa no topo do site e depois em “Criar conta”. Preencha nome, e-mail e senha. "
     "Enviaremos um link para o seu e-mail: clique nele para ativar a conta. Só depois disso é possível entrar."),
    ("conta", "Não recebi o e-mail de confirmação. E agora?",
     "Confira a caixa de spam e a aba Promoções. Se o e-mail não estiver lá, tente entrar na página de login: "
     "ela mostra um botão para reenviar o link de confirmação. O link vale por 3 dias."),
    ("conta", "Esqueci minha senha. Como recupero?",
     "Na página de login, clique em “Esqueci minha senha” e informe o e-mail da conta. Você receberá um link para "
     "criar uma senha nova. Por segurança, o link só funciona uma vez e expira em 3 dias."),
    ("conta", "Como desativo minha conta?",
     "Em Minha conta > Dados pessoais, use a opção “Desativar minha conta”. Antes, pause ou encerre seus anúncios "
     "ativos. O histórico de pedidos é mantido."),
    ("compras", "Quais formas de pagamento são aceitas?",
     "Cartão de crédito, cartão de débito, PIX e boleto. Você cadastra suas formas de pagamento em Minha conta > "
     "Pagamentos. Não guardamos o número completo do cartão, apenas a bandeira e os 4 últimos dígitos."),
    ("compras", "Posso comprar de vários vendedores de uma vez?",
     "Sim. Você finaliza tudo em um único checkout, e a compra é dividida em um pedido por vendedor, porque cada "
     "vendedor envia o próprio pacote. Por isso o frete é cobrado uma vez por vendedor."),
    ("compras", "Como cancelo um pedido?",
     "Enquanto o pedido estiver “Aguardando pagamento”, abra-o em Minha conta > Meus pedidos e clique em "
     "“Cancelar pedido”. Depois que o pagamento é aprovado, fale com a gente pela página de contato."),
    ("compras", "Como avalio um produto?",
     "Depois que você confirmar o recebimento do pedido, aparece a opção “Avaliar produto” em cada item, dentro "
     "de Meus pedidos. Só quem comprou e recebeu pode avaliar."),
    ("entrega", "Como o frete é calculado?",
     "O valor depende do estado de entrega e aparece na página do produto (informe seu CEP) e no checkout. "
     "Cada vendedor envia separadamente, então o frete é cobrado uma vez para cada vendedor da compra."),
    ("entrega", "Qual é o prazo de entrega?",
     "O prazo estimado, em dias úteis, aparece junto do frete e conta a partir do envio pelo vendedor."),
    ("entrega", "Como acompanho a entrega?",
     "Quando o vendedor enviar o pedido, você recebe um e-mail com o código de rastreio, que também fica "
     "disponível no detalhe do pedido, em Meus pedidos."),
    ("entrega", "Recebi meu pedido. Preciso fazer algo?",
     "Sim: abra o pedido em Meus pedidos e clique em “Confirmar recebimento”. Isso conclui a compra e libera "
     "a avaliação dos produtos."),
    ("vendas", "Como anuncio um produto?",
     "Clique em “Anunciar” no topo do site. Informe título, categoria, condição, descrição, preço e estoque, e "
     "envie até 8 fotos. O anúncio aparece na loja assim que é publicado como ativo."),
    ("vendas", "Onde vejo minhas vendas?",
     "Em Minha conta > Minhas vendas. Lá você vê o endereço de entrega de cada pedido, aprova o pagamento, "
     "marca como em preparação e informa o código de rastreio ao enviar. Você também recebe um e-mail a cada venda."),
    ("vendas", "Como respondo às perguntas dos compradores?",
     "Em Minha conta > Perguntas recebidas, ou direto na página do seu anúncio. O comprador é avisado por e-mail "
     "quando você responde."),
    ("seguranca", "Meus dados de cartão ficam salvos?",
     "Não. Guardamos apenas o tipo da forma de pagamento, a bandeira e os 4 últimos dígitos, para você "
     "identificar o cartão. Veja a Política de privacidade para mais detalhes."),
    ("seguranca", "A contratempo pede minha senha por e-mail?",
     "Nunca. Nossos e-mails só trazem links para o próprio site. Se receber um pedido de senha, não responda e "
     "avise a gente pela página de contato."),
]


def popular(apps, schema_editor):
    TabelaFrete = apps.get_model("marketplace", "TabelaFrete")
    for regiao, (ufs, valor, prazo) in REGIOES.items():
        for uf in ufs:
            TabelaFrete.objects.get_or_create(
                uf=uf, defaults={"regiao": regiao, "valor": valor, "prazo_dias": prazo}
            )

    PerguntaFrequente = apps.get_model("marketplace", "PerguntaFrequente")
    if not PerguntaFrequente.objects.exists():
        for ordem, (tema, pergunta, resposta) in enumerate(FAQ):
            PerguntaFrequente.objects.create(tema=tema, pergunta=pergunta, resposta=resposta, ordem=ordem)

    Pedido = apps.get_model("marketplace", "Pedido")
    ItemPedido = apps.get_model("marketplace", "ItemPedido")
    for pedido in Pedido.objects.filter(vendedor__isnull=True):
        item = (
            ItemPedido.objects.filter(pedido=pedido, produto__isnull=False)
            .select_related("produto").first()
        )
        if item:
            pedido.vendedor_id = item.produto.vendedor_id
            pedido.save(update_fields=["vendedor"])


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0002_frete_vendas_perguntas"),
    ]

    operations = [
        migrations.RunPython(popular, migrations.RunPython.noop),
    ]
