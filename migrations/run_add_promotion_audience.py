"""Aplica add_promotion_audience.sql de forma idempotente."""

from __future__ import annotations

import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from backend.db.database import SQLALCHEMY_DATABASE_URI  # noqa: E402


def _parse_mysql_uri(uri: str) -> dict[str, str | int]:
    # mysql+pymysql://user:pass@host:port/dbname
    without_scheme = uri.split("://", 1)[1]
    auth, host_db = without_scheme.split("@", 1)
    user, password = auth.split(":", 1)
    host_port, database = host_db.split("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, "3306"
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": int(port),
        "database": database,
    }


def main() -> None:
    cfg = _parse_mysql_uri(SQLALCHEMY_DATABASE_URI)
    conn = pymysql.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=int(cfg["port"]),
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM promotions LIKE 'audience_type'")
            if cur.fetchone() is None:
                cur.execute(
                    """
                    ALTER TABLE promotions
                      ADD COLUMN audience_type TINYINT NOT NULL DEFAULT 1
                      COMMENT '1=todos, 2=seleccionados'
                      AFTER status_id
                    """
                )
                print("OK: promotions.audience_type agregada")
            else:
                print("SKIP: promotions.audience_type ya existe")

            cur.execute("SHOW TABLES LIKE 'promotion_customers'")
            if cur.fetchone() is None:
                cur.execute(
                    """
                    CREATE TABLE promotion_customers (
                      id INT AUTO_INCREMENT PRIMARY KEY,
                      promotion_id INT NOT NULL,
                      customer_id INT NOT NULL,
                      added_date DATETIME NULL,
                      UNIQUE KEY uq_promotion_customer (promotion_id, customer_id),
                      KEY idx_promotion_customers_customer (customer_id),
                      CONSTRAINT fk_promotion_customers_promotion
                        FOREIGN KEY (promotion_id) REFERENCES promotions(id) ON DELETE CASCADE
                    )
                    """
                )
                print("OK: tabla promotion_customers creada")
            else:
                print("SKIP: promotion_customers ya existe")

        conn.commit()
        print("Migración completada")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
