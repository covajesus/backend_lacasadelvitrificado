CREATE TABLE IF NOT EXISTS campaign_access_tokens (
    id INT NOT NULL AUTO_INCREMENT,
    token VARCHAR(32) NOT NULL,
    customer_id INT NOT NULL,
    product_id INT NULL,
    campaign_id INT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    added_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_campaign_access_tokens_token (token),
    KEY ix_campaign_access_tokens_customer_id (customer_id),
    KEY ix_campaign_access_tokens_campaign_id (campaign_id),
    KEY ix_campaign_access_tokens_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
