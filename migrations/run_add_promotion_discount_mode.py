"""Agrega modo y monto de descuento en promociones."""

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
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM promotions LIKE 'discount_mode'")
            if not cur.fetchone():
                cur.execute(
                    """
                    ALTER TABLE promotions
                      ADD COLUMN discount_mode VARCHAR(20) NOT NULL DEFAULT 'percent'
                      AFTER discount_percent
                    """
                )
                print("OK: promotions.discount_mode agregada")
            else:
                print("SKIP: promotions.discount_mode ya existe")

            cur.execute("SHOW COLUMNS FROM promotions LIKE 'discount_amount'")
            if not cur.fetchone():
                cur.execute(
                    """
                    ALTER TABLE promotions
                      ADD COLUMN discount_amount DECIMAL(12, 2) NOT NULL DEFAULT 0
                      AFTER discount_mode
                    """
                )
                print("OK: promotions.discount_amount agregada")
            else:
                print("SKIP: promotions.discount_amount ya existe")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
