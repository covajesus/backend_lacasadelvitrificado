CREATE TABLE IF NOT EXISTS advertising_campaigns (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  message TEXT NOT NULL,
  image_path VARCHAR(500) NULL,
  audience_type TINYINT NOT NULL DEFAULT 1 COMMENT '1=todos, 2=seleccionados',
  status_id TINYINT NOT NULL DEFAULT 0 COMMENT '0=borrador, 1=enviada',
  sent_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  added_date DATETIME NULL,
  updated_date DATETIME NULL,
  sent_date DATETIME NULL
);

CREATE TABLE IF NOT EXISTS advertising_campaign_customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  campaign_id INT NOT NULL,
  customer_id INT NOT NULL,
  added_date DATETIME NULL,
  UNIQUE KEY uq_ad_campaign_customer (campaign_id, customer_id),
  KEY idx_ad_campaign_customers_campaign (campaign_id),
  KEY idx_ad_campaign_customers_customer (customer_id)
);
