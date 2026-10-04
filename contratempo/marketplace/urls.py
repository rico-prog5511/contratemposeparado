"""
marketplace/urls.py

Incluído em contratempo/contratempo/urls.py com:
    path("", include("marketplace.urls"))

Os nomes originais (home, sobre_nos, privacidade, produtos,
produto_detalhe, adicionar_ao_carrinho, carrinho, contato, perfil,
login) foram mantidos.
"""

from django.urls import path

from . import views, views_anuncios, views_checkout, views_conta, views_vendas

urlpatterns = [
    # ---------------------------------------------------------------
    # Vitrine e institucional
    # ---------------------------------------------------------------
    path("", views.home, name="home"),
    path("sobre-nos/", views.sobre_nos, name="sobre_nos"),
    path("privacidade/", views.privacidade, name="privacidade"),
    path("acessibilidade/", views.acessibilidade, name="acessibilidade"),
    path("cookies/", views.politica_cookies, name="politica_cookies"),
    path("guia/", views.guia, name="guia"),
    path("guia/<slug:slug>/", views.guia_artigo, name="guia_artigo"),
    path("contato/", views.contato, name="contato"),
    path("duvidas-frequentes/", views.faq, name="faq"),

    path("produtos/", views.produtos, name="produtos"),
    path("produtos/sugestoes/", views.sugestoes_busca, name="sugestoes_busca"),
    path("produtos/vistos/", views.produtos_vistos, name="produtos_vistos"),
    path("categorias/", views.categorias, name="categorias"),
    path("produtos/<int:produto_id>/", views.produto_detalhe, name="produto_detalhe"),
    path("produtos/<int:produto_id>/perguntar/", views.fazer_pergunta, name="fazer_pergunta"),
    path("produtos/<int:produto_id>/denunciar/", views.denunciar_produto, name="denunciar_produto"),
    path("vendedores/<int:usuario_id>/", views.vendedor_perfil, name="vendedor_perfil"),

    # ---------------------------------------------------------------
    # Carrinho
    # ---------------------------------------------------------------
    path("produtos/<int:produto_id>/carrinho/adicionar/", views.adicionar_ao_carrinho, name="adicionar_ao_carrinho"),
    path("carrinho/", views.carrinho, name="carrinho"),
    path("carrinho/item/<int:item_id>/atualizar/", views.atualizar_item_carrinho, name="atualizar_item_carrinho"),
    path("carrinho/item/<int:item_id>/remover/", views.remover_item_carrinho, name="remover_item_carrinho"),

    # ---------------------------------------------------------------
    # Checkout e pedidos (comprador)
    # ---------------------------------------------------------------
    path("checkout/", views_checkout.checkout_endereco, name="checkout_endereco"),
    path("checkout/pagamento/", views_checkout.checkout_pagamento, name="checkout_pagamento"),
    path("checkout/revisao/", views_checkout.checkout_revisao, name="checkout_revisao"),
    path("checkout/concluido/", views_checkout.pedido_concluido, name="pedido_concluido"),

    path("conta/pedidos/", views_checkout.pedidos, name="pedidos"),
    path("conta/pedidos/<int:pedido_id>/", views_checkout.pedido_detalhe, name="pedido_detalhe"),
    path("conta/pedidos/<int:pedido_id>/cancelar/", views_checkout.pedido_cancelar, name="pedido_cancelar"),
    path(
        "conta/pedidos/<int:pedido_id>/recebido/",
        views_checkout.pedido_confirmar_recebimento, name="pedido_confirmar_recebimento",
    ),
    path(
        "conta/pedidos/<int:pedido_id>/avaliar/<int:produto_id>/",
        views_checkout.avaliar_produto, name="avaliar_produto",
    ),

    # ---------------------------------------------------------------
    # Autenticação, confirmação de e-mail e recuperação de senha
    # ---------------------------------------------------------------
    path("login/", views_conta.login_view, name="login"),
    path("cadastro/", views_conta.cadastro, name="cadastro"),
    path("sair/", views_conta.logout_view, name="logout"),
    path("cadastro/confirmar/<uidb64>/<token>/", views_conta.confirmar_email, name="confirmar_email"),
    path("cadastro/reenviar/", views_conta.reenviar_confirmacao, name="reenviar_confirmacao"),

    path("senha/recuperar/", views_conta.RecuperarSenhaView.as_view(), name="password_reset"),
    path("senha/recuperar/enviado/", views_conta.RecuperarSenhaEnviadoView.as_view(), name="password_reset_done"),
    path("senha/nova/<uidb64>/<token>/", views_conta.NovaSenhaView.as_view(), name="password_reset_confirm"),
    path("senha/nova/concluido/", views_conta.NovaSenhaConcluidaView.as_view(), name="password_reset_complete"),

    # ---------------------------------------------------------------
    # Minha conta
    # ---------------------------------------------------------------
    path("conta/", views_conta.perfil, name="perfil"),
    path("conta/editar/", views_conta.editar_perfil, name="editar_perfil"),
    path("conta/senha/", views_conta.alterar_senha, name="alterar_senha"),
    path("conta/desativar/", views_conta.desativar_conta, name="desativar_conta"),

    path("conta/enderecos/", views_conta.enderecos, name="enderecos"),
    path("conta/enderecos/novo/", views_conta.endereco_form, name="endereco_criar"),
    path("conta/enderecos/<int:endereco_id>/editar/", views_conta.endereco_form, name="endereco_editar"),
    path("conta/enderecos/<int:endereco_id>/excluir/", views_conta.endereco_excluir, name="endereco_excluir"),
    path("conta/enderecos/<int:endereco_id>/principal/", views_conta.endereco_principal, name="endereco_principal"),

    path("conta/pagamentos/", views_conta.pagamentos, name="pagamentos"),
    path("conta/pagamentos/novo/", views_conta.pagamento_form, name="pagamento_criar"),
    path("conta/pagamentos/<int:forma_id>/editar/", views_conta.pagamento_form, name="pagamento_editar"),
    path("conta/pagamentos/<int:forma_id>/excluir/", views_conta.pagamento_excluir, name="pagamento_excluir"),
    path("conta/pagamentos/<int:forma_id>/principal/", views_conta.pagamento_principal, name="pagamento_principal"),

    # ---------------------------------------------------------------
    # Anúncios (área do vendedor)
    # ---------------------------------------------------------------
    path("anuncios/", views_anuncios.anuncios, name="anuncios"),
    path("anuncios/novo/", views_anuncios.anuncio_criar, name="anuncio_criar"),
    path("anuncios/estoque/", views_anuncios.estoque, name="estoque"),
    path("anuncios/<int:produto_id>/", views_anuncios.anuncio_detalhe, name="anuncio_detalhe"),
    path("anuncios/<int:produto_id>/editar/", views_anuncios.anuncio_editar, name="anuncio_editar"),
    path("anuncios/<int:produto_id>/status/", views_anuncios.anuncio_status, name="anuncio_status"),
    path("anuncios/<int:produto_id>/excluir/", views_anuncios.anuncio_excluir, name="anuncio_excluir"),

    # ---------------------------------------------------------------
    # Vendas e perguntas (área do vendedor)
    # ---------------------------------------------------------------
    path("vendas/", views_vendas.vendas, name="vendas"),
    path("vendas/<int:pedido_id>/", views_vendas.venda_detalhe, name="venda_detalhe"),
    path("vendas/<int:pedido_id>/avancar/", views_vendas.venda_avancar, name="venda_avancar"),
    path("vendas/<int:pedido_id>/cancelar/", views_vendas.venda_cancelar, name="venda_cancelar"),
    path("vendas/perguntas/", views_vendas.perguntas_recebidas, name="perguntas_recebidas"),
    path("vendas/perguntas/<int:pergunta_id>/responder/", views_vendas.responder_pergunta, name="responder_pergunta"),
]
