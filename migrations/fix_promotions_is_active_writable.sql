-- Writable is_active kept in sync with status_id for legacy API compatibility.
ALTER TABLE promotions DROP COLUMN IF EXISTS is_active;
ALTER TABLE promotions
  ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER status_id;
UPDATE promotions SET is_active = status_id;

DROP TRIGGER IF EXISTS promotions_bi_sync;
DROP TRIGGER IF EXISTS promotions_bu_sync;

DELIMITER //
CREATE TRIGGER promotions_bi_sync
BEFORE INSERT ON promotions
FOR EACH ROW
BEGIN
  SET NEW.status_id = COALESCE(NEW.status_id, NEW.is_active, 1);
  SET NEW.is_active = COALESCE(NEW.status_id, NEW.is_active, 1);
END//
CREATE TRIGGER promotions_bu_sync
BEFORE UPDATE ON promotions
FOR EACH ROW
BEGIN
  SET NEW.status_id = COALESCE(NEW.status_id, NEW.is_active, 1);
  SET NEW.is_active = COALESCE(NEW.status_id, NEW.is_active, 1);
END//
DELIMITER ;
