"""Crea tablas de campañas de publicidad de forma idempotente."""

from __future__ import annotations

import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from backend.db.database import SQLALCHEMY_DATABASE_URI  # noqa: E402


def _parse_mysql_uri(uri: str) -> dict[str, str | int]:
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
            cur.execute("SHOW TABLES LIKE 'advertising_campaigns'")
            if cur.fetchone() is None:
                cur.execute(
                    """
                    CREATE TABLE advertising_campaigns (
                      id INT AUTO_INCREMENT PRIMARY KEY,
                      name VARCHAR(255) NOT NULL,
                      message TEXT NOT NULL,
                      image_path VARCHAR(500) NULL,
                      audience_type TINYINT NOT NULL DEFAULT 1,
                      status_id TINYINT NOT NULL DEFAULT 0,
                      sent_count INT NOT NULL DEFAULT 0,
                      failed_count INT NOT NULL DEFAULT 0,
                      added_date DATETIME NULL,
                      updated_date DATETIME NULL,
                      sent_date DATETIME NULL
                    )
                    """
                )
                print("OK: tabla advertising_campaigns creada")
            else:
                print("SKIP: advertising_campaigns ya existe")

            cur.execute("SHOW TABLES LIKE 'advertising_campaign_customers'")
            if cur.fetchone() is None:
                cur.execute(
                    """
                    CREATE TABLE advertising_campaign_customers (
                      id INT AUTO_INCREMENT PRIMARY KEY,
                      campaign_id INT NOT NULL,
                      customer_id INT NOT NULL,
                      added_date DATETIME NULL,
                      UNIQUE KEY uq_ad_campaign_customer (campaign_id, customer_id),
                      KEY idx_ad_campaign_customers_campaign (campaign_id),
                      KEY idx_ad_campaign_customers_customer (customer_id)
                    )
                    """
                )
                print("OK: tabla advertising_campaign_customers creada")
            else:
                print("SKIP: advertising_campaign_customers ya existe")
        conn.commit()
        print("Migración completada")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
