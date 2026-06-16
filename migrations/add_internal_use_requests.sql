CREATE TABLE IF NOT EXISTS internal_use_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  description TEXT NOT NULL,
  notes TEXT NULL,
  sale_id INT NULL,
  subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0,
  tax DECIMAL(12, 2) NOT NULL DEFAULT 0,
  total DECIMAL(12, 2) NOT NULL DEFAULT 0,
  added_date DATETIME NULL,
  updated_date DATETIME NULL
);

CREATE TABLE IF NOT EXISTS internal_use_request_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  internal_use_request_id INT NOT NULL,
  product_id INT NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  unit_quantity DECIMAL(12, 4) NOT NULL DEFAULT 0,
  unit_cost DECIMAL(12, 2) NOT NULL DEFAULT 0,
  line_total DECIMAL(12, 2) NOT NULL DEFAULT 0,
  unit_measure VARCHAR(255) NULL,
  added_date DATETIME NULL,
  updated_date DATETIME NULL
);
