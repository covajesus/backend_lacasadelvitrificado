-- status_id: 1 = activa, 0 = inactiva
ALTER TABLE promotions
  CHANGE COLUMN is_active status_id TINYINT(1) NOT NULL DEFAULT 1;
