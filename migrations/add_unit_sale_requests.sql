CREATE TABLE IF NOT EXISTS unit_sale_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NULL,
  customer_rut VARCHAR(255) NOT NULL,
  customer_name VARCHAR(255) NOT NULL,
  notes TEXT NULL,
  sale_id INT NULL,
  subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0,
  tax DECIMAL(12, 2) NOT NULL DEFAULT 0,
  total DECIMAL(12, 2) NOT NULL DEFAULT 0,
  added_date DATETIME NULL,
  updated_date DATETIME NULL
);

CREATE TABLE IF NOT EXISTS unit_sale_request_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  unit_sale_request_id INT NOT NULL,
  product_id INT NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  unit_quantity DECIMAL(12, 4) NOT NULL DEFAULT 0,
  unit_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
  line_total DECIMAL(12, 2) NOT NULL DEFAULT 0,
  unit_measure VARCHAR(255) NULL,
  added_date DATETIME NULL,
  updated_date DATETIME NULL
);
