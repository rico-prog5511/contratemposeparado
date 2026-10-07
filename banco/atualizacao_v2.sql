SET NAMES utf8mb4;
USE `contratempo_db`;

START TRANSACTION;

ALTER TABLE `usuarios`
  ADD COLUMN `email_confirmado` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'contas criadas pelo site começam em 0 até clicar no link do e-mail' AFTER `last_login`;

ALTER TABLE `pedidos`
  MODIFY COLUMN `valor_total` decimal(10,2) NOT NULL COMMENT 'produtos + frete',
  ADD COLUMN `vendedor_id` bigint DEFAULT NULL COMMENT 'o checkout gera um pedido por vendedor' AFTER `usuario_id`,
  ADD COLUMN `valor_frete` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT 'incluído em valor_total' AFTER `valor_total`,
  ADD COLUMN `prazo_entrega_dias` smallint unsigned DEFAULT NULL COMMENT 'dias úteis após o envio' AFTER `valor_frete`,
  ADD COLUMN `codigo_rastreio` varchar(50) DEFAULT NULL AFTER `prazo_entrega_dias`,
  ADD COLUMN `data_envio` datetime DEFAULT NULL AFTER `codigo_rastreio`,
  ADD KEY `idx_pedidos_vendedor` (`vendedor_id`,`status_pedido`),
  ADD CONSTRAINT `fk_pedidos_vendedor` FOREIGN KEY (`vendedor_id`) REFERENCES `usuarios` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `chk_pedidos_valor_frete` CHECK ((`valor_frete` >= 0));

UPDATE `pedidos` p
  JOIN (
    SELECT ip.pedido_id, MIN(ip.id) AS primeiro_item
      FROM `itens_pedido` ip
     WHERE ip.produto_id IS NOT NULL
     GROUP BY ip.pedido_id
  ) x ON x.pedido_id = p.id
  JOIN `itens_pedido` ip ON ip.id = x.primeiro_item
  JOIN `produtos` pr ON pr.id = ip.produto_id
   SET p.vendedor_id = pr.vendedor_id
 WHERE p.vendedor_id IS NULL;

CREATE TABLE `tabela_frete` (
  `id` int NOT NULL AUTO_INCREMENT,
  `uf` char(2) NOT NULL,
  `regiao` enum('norte','nordeste','centro_oeste','sudeste','sul') NOT NULL,
  `valor` decimal(8,2) NOT NULL COMMENT 'cobrado uma vez por vendedor',
  `prazo_dias` smallint unsigned NOT NULL COMMENT 'dias úteis após o envio',
  `ativo` tinyint(1) NOT NULL DEFAULT '1' COMMENT '0 = UF não atendida',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tabela_frete_uf` (`uf`),
  CONSTRAINT `chk_tabela_frete_valor` CHECK ((`valor` >= 0)),
  CONSTRAINT `chk_tabela_frete_prazo` CHECK ((`prazo_dias` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Valor e prazo de frete por UF de destino';

CREATE TABLE `perguntas_frequentes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tema` enum('conta','compras','entrega','vendas','seguranca') NOT NULL,
  `pergunta` varchar(200) NOT NULL,
  `resposta` text NOT NULL,
  `ordem` smallint unsigned NOT NULL DEFAULT '0',
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_perguntas_frequentes_tema` (`tema`,`ordem`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Página de dúvidas frequentes (editável no admin)';

CREATE TABLE `perguntas_produto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `produto_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL COMMENT 'quem perguntou',
  `pergunta` text NOT NULL,
  `resposta` text COMMENT 'NULL = ainda sem resposta do vendedor',
  `status` enum('publicada','oculta') NOT NULL DEFAULT 'publicada' COMMENT 'moderação',
  `data_pergunta` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_resposta` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_perguntas_produto_produto` (`produto_id`,`status`),
  KEY `fk_perguntas_produto_usuario` (`usuario_id`),
  CONSTRAINT `fk_perguntas_produto_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_perguntas_produto_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Perguntas públicas dos compradores aos vendedores';

INSERT INTO `tabela_frete` (`uf`, `regiao`, `valor`, `prazo_dias`) VALUES
  ('SP', 'sudeste', '19.90', 5),
  ('RJ', 'sudeste', '19.90', 5),
  ('MG', 'sudeste', '19.90', 5),
  ('ES', 'sudeste', '19.90', 5),
  ('PR', 'sul', '24.90', 7),
  ('SC', 'sul', '24.90', 7),
  ('RS', 'sul', '24.90', 7),
  ('DF', 'centro_oeste', '29.90', 8),
  ('GO', 'centro_oeste', '29.90', 8),
  ('MT', 'centro_oeste', '29.90', 8),
  ('MS', 'centro_oeste', '29.90', 8),
  ('BA', 'nordeste', '34.90', 10),
  ('SE', 'nordeste', '34.90', 10),
  ('AL', 'nordeste', '34.90', 10),
  ('PE', 'nordeste', '34.90', 10),
  ('PB', 'nordeste', '34.90', 10),
  ('RN', 'nordeste', '34.90', 10),
  ('CE', 'nordeste', '34.90', 10),
  ('PI', 'nordeste', '34.90', 10),
  ('MA', 'nordeste', '34.90', 10),
  ('PA', 'norte', '39.90', 12),
  ('AP', 'norte', '39.90', 12),
  ('AM', 'norte', '39.90', 12),
  ('RR', 'norte', '39.90', 12),
  ('AC', 'norte', '39.90', 12),
  ('RO', 'norte', '39.90', 12),
  ('TO', 'norte', '39.90', 12);

INSERT INTO `perguntas_frequentes` (`tema`, `pergunta`, `resposta`, `ordem`) VALUES
  ('conta', 'Como crio minha conta?', 'Clique no ícone de pessoa no topo do site e depois em “Criar conta”. Preencha nome, e-mail e senha. Enviaremos um link para o seu e-mail: clique nele para ativar a conta. Só depois disso é possível entrar.', 0),
  ('conta', 'Não recebi o e-mail de confirmação. E agora?', 'Confira a caixa de spam e a aba Promoções. Se o e-mail não estiver lá, tente entrar na página de login: ela mostra um botão para reenviar o link de confirmação. O link vale por 3 dias.', 1),
  ('conta', 'Esqueci minha senha. Como recupero?', 'Na página de login, clique em “Esqueci minha senha” e informe o e-mail da conta. Você receberá um link para criar uma senha nova. Por segurança, o link só funciona uma vez e expira em 3 dias.', 2),
  ('conta', 'Como desativo minha conta?', 'Em Minha conta > Dados pessoais, use a opção “Desativar minha conta”. Antes, pause ou encerre seus anúncios ativos. O histórico de pedidos é mantido.', 3),
  ('compras', 'Quais formas de pagamento são aceitas?', 'Cartão de crédito, cartão de débito, PIX e boleto. Você cadastra suas formas de pagamento em Minha conta > Pagamentos. Não guardamos o número completo do cartão, apenas a bandeira e os 4 últimos dígitos.', 4),
  ('compras', 'Posso comprar de vários vendedores de uma vez?', 'Sim. Você finaliza tudo em um único checkout, e a compra é dividida em um pedido por vendedor, porque cada vendedor envia o próprio pacote. Por isso o frete é cobrado uma vez por vendedor.', 5),
  ('compras', 'Como cancelo um pedido?', 'Enquanto o pedido estiver “Aguardando pagamento”, abra-o em Minha conta > Meus pedidos e clique em “Cancelar pedido”. Depois que o pagamento é aprovado, fale com a gente pela página de contato.', 6),
  ('compras', 'Como avalio um produto?', 'Depois que você confirmar o recebimento do pedido, aparece a opção “Avaliar produto” em cada item, dentro de Meus pedidos. Só quem comprou e recebeu pode avaliar.', 7),
  ('entrega', 'Como o frete é calculado?', 'O valor depende do estado de entrega e aparece na página do produto (informe seu CEP) e no checkout. Cada vendedor envia separadamente, então o frete é cobrado uma vez para cada vendedor da compra.', 8),
  ('entrega', 'Qual é o prazo de entrega?', 'O prazo estimado, em dias úteis, aparece junto do frete e conta a partir do envio pelo vendedor.', 9),
  ('entrega', 'Como acompanho a entrega?', 'Quando o vendedor enviar o pedido, você recebe um e-mail com o código de rastreio, que também fica disponível no detalhe do pedido, em Meus pedidos.', 10),
  ('entrega', 'Recebi meu pedido. Preciso fazer algo?', 'Sim: abra o pedido em Meus pedidos e clique em “Confirmar recebimento”. Isso conclui a compra e libera a avaliação dos produtos.', 11),
  ('vendas', 'Como anuncio um produto?', 'Clique em “Anunciar” no topo do site. Informe título, categoria, condição, descrição, preço e estoque, e envie até 8 fotos. O anúncio aparece na loja assim que é publicado como ativo.', 12),
  ('vendas', 'Onde vejo minhas vendas?', 'Em Minha conta > Minhas vendas. Lá você vê o endereço de entrega de cada pedido, aprova o pagamento, marca como em preparação e informa o código de rastreio ao enviar. Você também recebe um e-mail a cada venda.', 13),
  ('vendas', 'Como respondo às perguntas dos compradores?', 'Em Minha conta > Perguntas recebidas, ou direto na página do seu anúncio. O comprador é avisado por e-mail quando você responde.', 14),
  ('seguranca', 'Meus dados de cartão ficam salvos?', 'Não. Guardamos apenas o tipo da forma de pagamento, a bandeira e os 4 últimos dígitos, para você identificar o cartão. Veja a Política de privacidade para mais detalhes.', 15),
  ('seguranca', 'A contratempo pede minha senha por e-mail?', 'Nunca. Nossos e-mails só trazem links para o próprio site. Se receber um pedido de senha, não responda e avise a gente pela página de contato.', 16);

INSERT INTO `django_migrations` (`app`, `name`, `applied`) VALUES
  ('marketplace', '0002_frete_vendas_perguntas', NOW(6)),
  ('marketplace', '0003_dados_iniciais', NOW(6));

COMMIT;
