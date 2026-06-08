-- Vincula solicitudes de muestra con el pedido (sale) generado automáticamente
ALTER TABLE sample_requests
  ADD COLUMN sale_id INT NULL AFTER notes;
