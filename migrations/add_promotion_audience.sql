ALTER TABLE promotions
  ADD COLUMN audience_type TINYINT NOT NULL DEFAULT 1 COMMENT '1=todos, 2=seleccionados' AFTER status_id;

CREATE TABLE IF NOT EXISTS promotion_customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  promotion_id INT NOT NULL,
  customer_id INT NOT NULL,
  added_date DATETIME NULL,
  UNIQUE KEY uq_promotion_customer (promotion_id, customer_id),
  KEY idx_promotion_customers_customer (customer_id),
  CONSTRAINT fk_promotion_customers_promotion
    FOREIGN KEY (promotion_id) REFERENCES promotions(id) ON DELETE CASCADE
);
