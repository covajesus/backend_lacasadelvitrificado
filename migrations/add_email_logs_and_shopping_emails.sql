-- Emails secundarios / aduana en compras + log de fallos de envío
ALTER TABLE shoppings
  ADD COLUMN IF NOT EXISTS second_email VARCHAR(255) NULL AFTER email,
  ADD COLUMN IF NOT EXISTS third_email VARCHAR(255) NULL AFTER second_email,
  ADD COLUMN IF NOT EXISTS customs_company_email VARCHAR(255) NULL AFTER third_email;

CREATE TABLE IF NOT EXISTS email_logs (
  id INT NOT NULL AUTO_INCREMENT,
  entity_type VARCHAR(50) NOT NULL,
  entity_id INT NOT NULL,
  email_type VARCHAR(50) NOT NULL,
  recipient VARCHAR(255) NULL,
  cc VARCHAR(500) NULL,
  subject VARCHAR(255) NULL,
  status VARCHAR(20) NOT NULL,
  error_message TEXT NULL,
  trigger_source VARCHAR(50) NULL,
  added_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_email_logs_entity (entity_type, entity_id),
  KEY ix_email_logs_status (status),
  KEY ix_email_logs_added_date (added_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
