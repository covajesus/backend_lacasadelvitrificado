-- Migración para agregar el campo shopping_number a la tabla shoppings
-- Ejecutar este script en la base de datos

ALTER TABLE shoppings ADD COLUMN shopping_number VARCHAR(100);

-- Opcional: Agregar comentario a la columna
COMMENT ON COLUMN shoppings.shopping_number IS 'Número de referencia de la compra';
