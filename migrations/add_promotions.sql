CREATE TABLE IF NOT EXISTS promotions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  promotion_type_id INT NOT NULL DEFAULT 1,
  product_id INT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  discount_percent DECIMAL(5, 2) NOT NULL DEFAULT 0,
  coupon_code VARCHAR(50) NULL,
  minimum_purchase DECIMAL(12, 2) NOT NULL DEFAULT 0,
  start_date DATETIME NULL,
  end_date DATETIME NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  added_date DATETIME NULL,
  updated_date DATETIME NULL,
  UNIQUE KEY uq_promotions_coupon_code (coupon_code)
);

CREATE TABLE IF NOT EXISTS promotion_products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  promotion_id INT NOT NULL,
  product_id INT NOT NULL,
  original_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
  promotional_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
  discount_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
  added_date DATETIME NULL,
  UNIQUE KEY uq_promotion_product (promotion_id, product_id),
  KEY idx_promotion_products_product (product_id),
  CONSTRAINT fk_promotion_products_promotion
    FOREIGN KEY (promotion_id) REFERENCES promotions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS promotion_usages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  promotion_id INT NOT NULL,
  promotion_type_id INT NOT NULL,
  product_id INT NULL,
  sale_id INT NULL,
  budget_id INT NULL,
  coupon_code VARCHAR(50) NULL,
  quantity INT NOT NULL DEFAULT 1,
  original_unit_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
  promotional_unit_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
  discount_amount_per_unit DECIMAL(12, 2) NOT NULL DEFAULT 0,
  total_discount_lost DECIMAL(12, 2) NOT NULL DEFAULT 0,
  applied_date DATETIME NULL,
  KEY idx_promotion_usages_promotion (promotion_id),
  KEY idx_promotion_usages_sale (sale_id),
  KEY idx_promotion_usages_budget (budget_id),
  CONSTRAINT fk_promotion_usages_promotion
    FOREIGN KEY (promotion_id) REFERENCES promotions(id)
);
