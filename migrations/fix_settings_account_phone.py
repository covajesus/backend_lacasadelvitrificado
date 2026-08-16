"""Tipa phone como VARCHAR (antes bigint no aceptaba +56...)."""
import pymysql

conn = pymysql.connect(
    host="31.97.250.169",
    user="admin",
    password="Admin2020!",
    database="lacasadelvitrificado",
    charset="utf8mb4",
)
cur = conn.cursor()

cur.execute("SELECT account_number, phone FROM settings WHERE id = 1")
print("before:", cur.fetchone())

cur.execute("ALTER TABLE settings MODIFY COLUMN phone VARCHAR(255) NULL")
conn.commit()

cur.execute("SELECT account_number, phone FROM settings WHERE id = 1")
print("after alter:", cur.fetchone())
cur.execute(
    "SHOW FULL COLUMNS FROM settings WHERE Field IN ('account_number', 'phone')"
)
print("cols:", cur.fetchall())
conn.close()
print("OK")
