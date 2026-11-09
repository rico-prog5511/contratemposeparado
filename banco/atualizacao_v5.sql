SET NAMES utf8mb4;
USE `contratempo_db`;

ALTER TABLE `denuncias`
  MODIFY `motivo` enum('falsificado','proibido','adulto','enganoso','golpe','ofensivo','outro') NOT NULL;

INSERT INTO `django_migrations` (`app`, `name`, `applied`) VALUES
  ('marketplace', '0006_denuncia_motivo_adulto', NOW(6));
