-- Migración para agregar el campo shopping_number a la tabla shopping
-- Ejecutar este script en la base de datos

ALTER TABLE shopping ADD COLUMN shopping_number VARCHAR(100) DEFAULT NULL;

-- Comentario: Este campo almacena el número personalizado de la orden de compra
