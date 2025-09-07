-- Migración para agregar el campo prepaid_discount a la tabla settings
-- Fecha: 2025-09-07

ALTER TABLE settings ADD COLUMN prepaid_discount DECIMAL(5,2) DEFAULT NULL;

-- Comentario: Este campo almacena el porcentaje de descuento para prepagos
-- Ejemplo: 5.00 para 5% de descuento
