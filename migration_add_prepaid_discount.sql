-- Migración para agregar el campo prepaid_discount a la tabla settings
-- Ejecutar este script en la base de datos

ALTER TABLE settings ADD COLUMN prepaid_discount DECIMAL(5,2) DEFAULT 0.00;

-- Opcional: Agregar comentario a la columna
COMMENT ON COLUMN settings.prepaid_discount IS 'Porcentaje de descuento por prepago (ej: 5.00 para 5%)';
