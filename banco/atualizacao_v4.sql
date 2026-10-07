SET NAMES utf8mb4;
USE `contratempo_db`;

DELETE FROM `formas_pagamento` WHERE `tipo` NOT IN ('cartao_credito', 'cartao_debito');

UPDATE `formas_pagamento` f
JOIN (
  SELECT MIN(`id`) AS `id` FROM `formas_pagamento`
  GROUP BY `usuario_id`
  HAVING SUM(`principal`) = 0
) sem_principal ON sem_principal.`id` = f.`id`
SET f.`principal` = 1;

ALTER TABLE `formas_pagamento`
  MODIFY `tipo` enum('cartao_credito','cartao_debito') NOT NULL COMMENT 'PIX e boleto são escolhidos no checkout, sem cadastro',
  MODIFY `bandeira` varchar(30) DEFAULT NULL COMMENT 'Visa, Mastercard, Elo, American Express ou Hipercard',
  ADD COLUMN `validade_mes` smallint unsigned DEFAULT NULL AFTER `bandeira`,
  ADD COLUMN `validade_ano` smallint unsigned DEFAULT NULL COMMENT 'com 4 dígitos; número completo e CVV nunca são guardados' AFTER `validade_mes`;

INSERT INTO `django_migrations` (`app`, `name`, `applied`) VALUES
  ('marketplace', '0005_cartoes_validade', NOW(6));
