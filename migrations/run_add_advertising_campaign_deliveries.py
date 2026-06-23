"""Crea advertising_campaign_deliveries de forma idempotente."""

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
            cur.execute("SHOW TABLES LIKE 'advertising_campaign_deliveries'")
            if cur.fetchone() is None:
                sql_path = Path(__file__).resolve().parent / "add_advertising_campaign_deliveries.sql"
                cur.execute(sql_path.read_text(encoding="utf-8"))
                print("OK: tabla advertising_campaign_deliveries creada")
            else:
                print("SKIP: advertising_campaign_deliveries ya existe")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
