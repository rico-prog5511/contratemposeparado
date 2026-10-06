-- =====================================================================
-- CONTRATEMPO — script completo do banco de dados (MySQL 8.0+)
--
-- Cria o banco do zero, já na versão 3 (frete, vendas por vendedor,
-- confirmação de e-mail, perguntas frequentes, perguntas ao vendedor e
-- denúncias de anúncios). Gerado a partir do esquema real do
-- contratempo_db + migrations do Django (marketplace 0001 a 0004).
--
-- USO (instalação nova):
--   mysql -u root -p < banco/contratempo_db.sql
--   python manage.py migrate      <- não cria tabelas (já estão marcadas
--                                     como aplicadas); só registra os
--                                     content types e as permissões do admin
--   python manage.py createsuperuser
--
-- ATENÇÃO: para um banco que JÁ EXISTE, não use este arquivo — use
-- `python manage.py migrate` ou banco/atualizacao_v2.sql.
--
-- Não contém dados pessoais (usuários, pedidos, senhas). Contém só os
-- dados de referência: categorias, franquias, tabela de frete e FAQ.
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '-03:00';

CREATE DATABASE IF NOT EXISTS `contratempo_db`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE `contratempo_db`;

SET FOREIGN_KEY_CHECKS = 0;


-- =====================================================================
-- 1. USUÁRIOS E DADOS PESSOAIS
-- =====================================================================

CREATE TABLE `usuarios` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nome_completo` varchar(150) NOT NULL,
  `email` varchar(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `senha` varchar(128) NOT NULL COMMENT 'hash de senha (Django password hasher)',
  `data_nascimento` date DEFAULT NULL,
  `telefone` varchar(20) DEFAULT NULL,
  `avatar` varchar(255) DEFAULT NULL COMMENT 'caminho/URL da foto de perfil',
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_atualizacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status_conta` enum('ativo','inativo','suspenso') NOT NULL DEFAULT 'ativo',
  `is_active` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'flag de login exigido pelo Django',
  `is_staff` tinyint(1) NOT NULL DEFAULT '0',
  `is_superuser` tinyint(1) NOT NULL DEFAULT '0',
  `last_login` datetime DEFAULT NULL,
  `email_confirmado` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'contas criadas pelo site começam em 0 até clicar no link do e-mail',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuarios_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Usuários da plataforma (compradores/vendedores)';

CREATE TABLE `enderecos` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `nome_endereco` varchar(100) NOT NULL COMMENT 'ex: Casa, Trabalho',
  `cep` varchar(10) NOT NULL,
  `logradouro` varchar(150) NOT NULL,
  `numero` varchar(20) NOT NULL,
  `complemento` varchar(100) DEFAULT NULL,
  `bairro` varchar(100) NOT NULL,
  `cidade` varchar(100) NOT NULL,
  `estado` char(2) NOT NULL,
  `pais` varchar(60) NOT NULL DEFAULT 'Brasil',
  `endereco_principal` tinyint(1) NOT NULL DEFAULT '0',
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_enderecos_usuario` (`usuario_id`),
  CONSTRAINT `fk_enderecos_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Endereços cadastrados pelos usuários';

CREATE TABLE `formas_pagamento` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `tipo` enum('cartao_credito','cartao_debito') NOT NULL COMMENT 'PIX e boleto são escolhidos no checkout, sem cadastro',
  `apelido` varchar(60) DEFAULT NULL,
  `ultimos_digitos` char(4) DEFAULT NULL,
  `bandeira` varchar(30) DEFAULT NULL COMMENT 'Visa, Mastercard, Elo, American Express ou Hipercard',
  `validade_mes` smallint unsigned DEFAULT NULL,
  `validade_ano` smallint unsigned DEFAULT NULL COMMENT 'com 4 dígitos; número completo e CVV nunca são guardados',
  `token_externo` varchar(255) DEFAULT NULL COMMENT 'identificador tokenizado do gateway de pagamento',
  `principal` tinyint(1) NOT NULL DEFAULT '0',
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_formas_pagamento_usuario` (`usuario_id`),
  CONSTRAINT `fk_formas_pagamento_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Formas de pagamento associadas ao usuário (sem dados sensíveis de cartão)';


-- =====================================================================
-- 2. CATÁLOGO
-- =====================================================================

CREATE TABLE `categorias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(80) NOT NULL,
  `slug` varchar(90) NOT NULL,
  `descricao` varchar(255) DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_categorias_nome` (`nome`),
  UNIQUE KEY `uq_categorias_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Categorias de produtos (Jogos, Consoles, Quadrinhos, etc.)';

CREATE TABLE `franquias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `slug` varchar(110) NOT NULL,
  `descricao` varchar(255) DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_franquias_nome` (`nome`),
  UNIQUE KEY `uq_franquias_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Franquias relacionadas aos produtos (Pokémon, Marvel, Star Wars, etc.)';

CREATE TABLE `produtos` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `vendedor_id` bigint NOT NULL,
  `categoria_id` int NOT NULL,
  `franquia_id` int DEFAULT NULL,
  `nome` varchar(150) NOT NULL,
  `descricao` text NOT NULL,
  `preco` decimal(10,2) NOT NULL,
  `quantidade_disponivel` int NOT NULL DEFAULT '0',
  `condicao` enum('novo','usado','semi_novo') NOT NULL DEFAULT 'usado',
  `marca` varchar(80) DEFAULT NULL,
  `ano` smallint DEFAULT NULL,
  `sku` varchar(50) DEFAULT NULL COMMENT 'código identificador do anúncio',
  `status_anuncio` enum('ativo','pausado','vendido','encerrado') NOT NULL DEFAULT 'ativo',
  `data_criacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_atualizacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_produtos_sku` (`sku`),
  KEY `idx_produtos_categoria` (`categoria_id`),
  KEY `idx_produtos_franquia` (`franquia_id`),
  KEY `idx_produtos_vendedor` (`vendedor_id`),
  KEY `idx_produtos_status` (`status_anuncio`),
  KEY `idx_produtos_nome` (`nome`),
  FULLTEXT KEY `idx_produtos_busca` (`nome`,`descricao`),
  CONSTRAINT `fk_produtos_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_produtos_franquia` FOREIGN KEY (`franquia_id`) REFERENCES `franquias` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_produtos_vendedor` FOREIGN KEY (`vendedor_id`) REFERENCES `usuarios` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_produtos_preco` CHECK ((`preco` >= 0)),
  CONSTRAINT `chk_produtos_quantidade` CHECK ((`quantidade_disponivel` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Anúncios de produtos colecionáveis cadastrados pelos vendedores';

CREATE TABLE `produto_imagens` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `produto_id` bigint NOT NULL,
  `url_imagem` varchar(255) NOT NULL COMMENT 'caminho relativo gerado pelo ImageField do Django',
  `principal` tinyint(1) NOT NULL DEFAULT '0',
  `ordem_exibicao` smallint NOT NULL DEFAULT '0',
  `data_cadastro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_produto_imagens_produto` (`produto_id`),
  CONSTRAINT `fk_produto_imagens_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Imagens vinculadas a cada produto';


-- =====================================================================
-- 3. CARRINHO
-- =====================================================================

CREATE TABLE `carrinhos` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `status` enum('ativo','finalizado','abandonado') NOT NULL DEFAULT 'ativo',
  `data_criacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_atualizacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `usuario_carrinho_ativo` bigint GENERATED ALWAYS AS ((case when (`status` = _utf8mb4'ativo') then `usuario_id` else NULL end)) VIRTUAL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_carrinho_ativo_por_usuario` (`usuario_carrinho_ativo`),
  KEY `fk_carrinhos_usuario` (`usuario_id`),
  CONSTRAINT `fk_carrinhos_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Carrinho de compras do usuário (histórico de carrinhos permitido)';

CREATE TABLE `itens_carrinho` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `carrinho_id` bigint NOT NULL,
  `produto_id` bigint NOT NULL,
  `quantidade` int NOT NULL DEFAULT '1',
  `preco_unitario` decimal(10,2) NOT NULL COMMENT 'preço do produto no momento da inclusão',
  `data_adicionado` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_itens_carrinho` (`carrinho_id`,`produto_id`),
  KEY `fk_itens_carrinho_produto` (`produto_id`),
  CONSTRAINT `fk_itens_carrinho_carrinho` FOREIGN KEY (`carrinho_id`) REFERENCES `carrinhos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_itens_carrinho_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_itens_carrinho_quantidade` CHECK ((`quantidade` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Itens (produtos) dentro de um carrinho';


-- =====================================================================
-- 4. PEDIDOS
-- =====================================================================

CREATE TABLE `pedidos` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `endereco_id` bigint DEFAULT NULL,
  `forma_pagamento_id` bigint DEFAULT NULL,
  `endereco_snapshot` varchar(500) NOT NULL COMMENT 'cópia do endereço usado na compra',
  `forma_pagamento_snapshot` varchar(150) NOT NULL COMMENT 'cópia da forma de pagamento usada na compra',
  `status_pedido` enum('aguardando_pagamento','pagamento_aprovado','processamento','enviado','entregue','cancelado') NOT NULL DEFAULT 'aguardando_pagamento',
  `valor_total` decimal(10,2) NOT NULL COMMENT 'produtos + frete',
  `vendedor_id` bigint DEFAULT NULL COMMENT 'o checkout gera um pedido por vendedor',
  `valor_frete` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT 'incluído em valor_total',
  `prazo_entrega_dias` smallint unsigned DEFAULT NULL COMMENT 'dias úteis após o envio',
  `codigo_rastreio` varchar(50) DEFAULT NULL,
  `data_envio` datetime DEFAULT NULL,
  `data_criacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_atualizacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_pedidos_endereco` (`endereco_id`),
  KEY `fk_pedidos_forma_pagamento` (`forma_pagamento_id`),
  KEY `idx_pedidos_usuario` (`usuario_id`),
  KEY `idx_pedidos_status` (`status_pedido`),
  CONSTRAINT `fk_pedidos_endereco` FOREIGN KEY (`endereco_id`) REFERENCES `enderecos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_pedidos_forma_pagamento` FOREIGN KEY (`forma_pagamento_id`) REFERENCES `formas_pagamento` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_pedidos_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_pedidos_valor_total` CHECK ((`valor_total` >= 0)),
  KEY `idx_pedidos_vendedor` (`vendedor_id`,`status_pedido`),
  CONSTRAINT `fk_pedidos_vendedor` FOREIGN KEY (`vendedor_id`) REFERENCES `usuarios` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_pedidos_valor_frete` CHECK ((`valor_frete` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Pedidos realizados pelos usuários';

CREATE TABLE `itens_pedido` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pedido_id` bigint NOT NULL,
  `produto_id` bigint DEFAULT NULL,
  `nome_produto` varchar(150) NOT NULL COMMENT 'nome do produto no momento da compra',
  `preco_unitario` decimal(10,2) NOT NULL COMMENT 'preço unitário no momento da compra',
  `quantidade` int NOT NULL,
  `subtotal` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_itens_pedido_pedido` (`pedido_id`),
  KEY `idx_itens_pedido_produto` (`produto_id`),
  CONSTRAINT `fk_itens_pedido_pedido` FOREIGN KEY (`pedido_id`) REFERENCES `pedidos` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_itens_pedido_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `chk_itens_pedido_quantidade` CHECK ((`quantidade` > 0)),
  CONSTRAINT `chk_itens_pedido_subtotal` CHECK ((`subtotal` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Itens comprados em cada pedido (histórico preservado mesmo se o produto mudar)';


-- =====================================================================
-- 5. PÓS-VENDA E ATENDIMENTO
-- =====================================================================

CREATE TABLE `avaliacoes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `produto_id` bigint NOT NULL,
  `pedido_id` bigint NOT NULL,
  `nota` tinyint NOT NULL,
  `comentario` text,
  `data_avaliacao` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('publicada','oculta','removida') NOT NULL DEFAULT 'publicada',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_avaliacoes_usuario_produto_pedido` (`usuario_id`,`produto_id`,`pedido_id`),
  KEY `fk_avaliacoes_pedido` (`pedido_id`),
  KEY `idx_avaliacoes_produto` (`produto_id`),
  KEY `idx_avaliacoes_usuario` (`usuario_id`),
  CONSTRAINT `fk_avaliacoes_pedido` FOREIGN KEY (`pedido_id`) REFERENCES `pedidos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_avaliacoes_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_avaliacoes_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_avaliacoes_nota` CHECK ((`nota` between 1 and 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Avaliações de produtos feitas após a compra (regra de compra validada pelo Django)';

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

CREATE TABLE `contatos` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint DEFAULT NULL COMMENT 'NULL quando enviado por visitante não autenticado',
  `nome` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `assunto` varchar(150) NOT NULL,
  `mensagem` text NOT NULL,
  `status` enum('pendente','respondido','arquivado') NOT NULL DEFAULT 'pendente',
  `data_envio` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_contatos_usuario` (`usuario_id`),
  KEY `idx_contatos_status` (`status`),
  CONSTRAINT `fk_contatos_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Mensagens enviadas pela página de contato (login opcional)';

CREATE TABLE `denuncias` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `produto_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL COMMENT 'quem denunciou (não é mostrado ao vendedor)',
  `motivo` enum('falsificado','proibido','enganoso','golpe','ofensivo','outro') NOT NULL,
  `descricao` text,
  `status` enum('pendente','procedente','improcedente') NOT NULL DEFAULT 'pendente' COMMENT 'procedente = anúncio encerrado',
  `data_denuncia` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_analise` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_denuncias_status` (`status`),
  KEY `fk_denuncias_produto` (`produto_id`),
  KEY `fk_denuncias_usuario` (`usuario_id`),
  CONSTRAINT `fk_denuncias_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_denuncias_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Denúncias de anúncios, analisadas no admin';


-- =====================================================================
-- 6. FRETE E AJUDA
-- =====================================================================

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


-- =====================================================================
-- 7. TABELAS INTERNAS DO DJANGO (auth, admin, sessões, migrations)
-- =====================================================================

CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `usuarios_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuarios_groups` (`usuario_id`,`group_id`),
  KEY `fk_usuarios_groups_group` (`group_id`),
  CONSTRAINT `fk_usuarios_groups_group` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_usuarios_groups_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `fk_django_admin_log_usuario` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `fk_django_admin_log_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE,
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `usuarios_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `usuario_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuarios_user_permissions` (`usuario_id`,`permission_id`),
  KEY `fk_usuarios_user_permissions_permission` (`permission_id`),
  CONSTRAINT `fk_usuarios_user_permissions_permission` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_usuarios_user_permissions_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- 8. VIEWS
-- =====================================================================

CREATE OR REPLACE VIEW `vw_pedidos_resumo` AS select `ped`.`id` AS `pedido_id`,`ped`.`usuario_id` AS `usuario_id`,`ped`.`status_pedido` AS `status_pedido`,`ped`.`valor_total` AS `valor_total`,`ped`.`data_criacao` AS `data_criacao`,count(`ip`.`id`) AS `total_itens` from (`pedidos` `ped` left join `itens_pedido` `ip` on((`ip`.`pedido_id` = `ped`.`id`))) group by `ped`.`id`,`ped`.`usuario_id`,`ped`.`status_pedido`,`ped`.`valor_total`,`ped`.`data_criacao`;
CREATE OR REPLACE VIEW `vw_produtos_ativos` AS select `p`.`id` AS `id`,`p`.`nome` AS `nome`,`p`.`preco` AS `preco`,`p`.`quantidade_disponivel` AS `quantidade_disponivel`,`p`.`condicao` AS `condicao`,`c`.`nome` AS `categoria`,`f`.`nome` AS `franquia`,`p`.`vendedor_id` AS `vendedor_id`,`pi`.`url_imagem` AS `imagem_principal` from (((`produtos` `p` join `categorias` `c` on((`c`.`id` = `p`.`categoria_id`))) left join `franquias` `f` on((`f`.`id` = `p`.`franquia_id`))) left join `produto_imagens` `pi` on(((`pi`.`produto_id` = `p`.`id`) and (`pi`.`principal` = 1)))) where (`p`.`status_anuncio` = 'ativo');

-- =====================================================================
-- 9. DADOS DE REFERÊNCIA
-- =====================================================================

INSERT INTO `categorias` (`id`, `nome`, `slug`, `descricao`, `ativo`) VALUES
  (1, 'Jogos', 'jogos', 'Jogos físicos e de tabuleiro', 1),
  (2, 'Consoles', 'consoles', 'Consoles de videogame novos e retrô', 1),
  (3, 'Livros', 'livros', 'Livros diversos', 1),
  (4, 'Quadrinhos', 'quadrinhos', 'HQs, mangás e graphic novels', 1),
  (5, 'Música', 'musica', 'CDs, vinis e itens musicais', 1),
  (6, 'Filmes', 'filmes', 'DVDs, Blu-rays e itens de cinema', 1),
  (7, 'Roupas', 'roupas', 'Vestuário licenciado', 1),
  (8, 'Colecionáveis', 'colecionaveis', 'Cartas, miniaturas e itens de coleção', 1),
  (9, 'Brinquedos', 'brinquedos', 'Brinquedos e action figures', 1),
  (10, 'Outros', 'outros', 'Demais categorias', 1),
  (11, 'Discos', 'discos', 'Vinis, CD\'s, fitas de música', 1);

INSERT INTO `franquias` (`id`, `nome`, `slug`, `descricao`, `ativo`) VALUES
  (1, 'Pokémon', 'pokemon', 'Franquia Pokémon', 1),
  (2, 'Nintendo', 'nintendo', 'Jogos e produtos Nintendo', 1),
  (3, 'PlayStation', 'playstation', 'Jogos e produtos PlayStation', 1),
  (4, 'Xbox', 'xbox', 'Jogos e produtos Xbox', 1),
  (5, 'Marvel', 'marvel', 'Universo Marvel', 1),
  (6, 'DC', 'dc', 'Universo DC', 1),
  (7, 'Star Wars', 'star-wars', 'Franquia Star Wars', 1),
  (8, 'Harry Potter', 'harry-potter', 'Franquia Harry Potter', 1),
  (9, 'Senhor dos Anéis', 'senhor-dos-aneis', 'Franquia O Senhor dos Anéis', 1),
  (10, 'The Witcher', 'the-witcher', 'Todos os produtos de The Witcher', 1);

-- Valores de exemplo por região — ajuste em /admin/ > Tabela de frete.
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

-- =====================================================================
-- 10. REGISTRO DAS MIGRATIONS DO DJANGO
-- =====================================================================

-- Diz ao Django que estas tabelas já existem (evita que o `migrate` tente recriá-las).
INSERT INTO `django_migrations` (`app`, `name`, `applied`) VALUES
  ('contenttypes', '0001_initial', NOW(6)),
  ('contenttypes', '0002_remove_content_type_name', NOW(6)),
  ('auth', '0001_initial', NOW(6)),
  ('auth', '0002_alter_permission_name_max_length', NOW(6)),
  ('auth', '0003_alter_user_email_max_length', NOW(6)),
  ('auth', '0004_alter_user_username_opts', NOW(6)),
  ('auth', '0005_alter_user_last_login_null', NOW(6)),
  ('auth', '0006_require_contenttypes_0002', NOW(6)),
  ('auth', '0007_alter_validators_add_error_messages', NOW(6)),
  ('auth', '0008_alter_user_username_max_length', NOW(6)),
  ('auth', '0009_alter_user_last_name_max_length', NOW(6)),
  ('auth', '0010_alter_group_name_max_length', NOW(6)),
  ('auth', '0011_update_proxy_permissions', NOW(6)),
  ('auth', '0012_alter_user_first_name_max_length', NOW(6)),
  ('marketplace', '0001_initial', NOW(6)),
  ('admin', '0001_initial', NOW(6)),
  ('admin', '0002_logentry_remove_auto_add', NOW(6)),
  ('admin', '0003_logentry_add_action_flag_choices', NOW(6)),
  ('sessions', '0001_initial', NOW(6)),
  ('marketplace', '0002_frete_vendas_perguntas', NOW(6)),
  ('marketplace', '0003_dados_iniciais', NOW(6)),
  ('marketplace', '0004_denuncias', NOW(6)),
  ('marketplace', '0005_cartoes_validade', NOW(6));

SET FOREIGN_KEY_CHECKS = 1;
