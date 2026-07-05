-- Descuento decimal por línea de compra (ej. 49.5 %)
ALTER TABLE shoppings_products
  MODIFY COLUMN discount_percentage DOUBLE NULL;
