-- Backward compatibility: API legacy still reads promotions.is_active
-- Source of truth remains status_id (1 = activa, 0 = inactiva).
ALTER TABLE promotions
  ADD COLUMN is_active TINYINT(1) GENERATED ALWAYS AS (status_id) STORED;
