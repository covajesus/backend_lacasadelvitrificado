-- Guarda el cupón aplicado en la venta para registrar uso al aceptar el pago.
ALTER TABLE sales
  ADD COLUMN coupon_code VARCHAR(50) NULL AFTER delivery_address;
