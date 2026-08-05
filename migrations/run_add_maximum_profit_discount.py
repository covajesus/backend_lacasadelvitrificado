"""Agrega el máximo porcentaje de ganancia sacrificable en promociones."""

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
            cur.execute(
                "SHOW COLUMNS FROM settings LIKE 'maximum_profit_discount_percent'"
            )
            if cur.fetchone() is None:
                cur.execute(
                    """
                    ALTER TABLE settings
                      ADD COLUMN maximum_profit_discount_percent INT NOT NULL DEFAULT 100
                      AFTER prepaid_discount
                    """
                )
                print("OK: settings.maximum_profit_discount_percent agregada")
            else:
                print("SKIP: settings.maximum_profit_discount_percent ya existe")
        conn.commit()
        print("Migración completada")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
