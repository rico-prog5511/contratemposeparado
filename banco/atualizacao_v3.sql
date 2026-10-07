SET NAMES utf8mb4;
USE `contratempo_db`;

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

INSERT INTO `django_migrations` (`app`, `name`, `applied`) VALUES
  ('marketplace', '0004_denuncias', NOW(6));
