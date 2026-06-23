CREATE TABLE IF NOT EXISTS advertising_campaign_deliveries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  campaign_id INT NOT NULL,
  customer_id INT NOT NULL,
  message_id VARCHAR(255) NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  error_code VARCHAR(50) NULL,
  error_message TEXT NULL,
  sent_date DATETIME NULL,
  delivered_date DATETIME NULL,
  read_date DATETIME NULL,
  added_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_acd_campaign (campaign_id),
  INDEX idx_acd_message (message_id),
  INDEX idx_acd_customer (customer_id)
);
