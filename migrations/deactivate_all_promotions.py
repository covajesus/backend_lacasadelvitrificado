"""Desactiva todas las promociones vigentes."""
import pymysql

conn = pymysql.connect(
    host="31.97.250.169",
    user="admin",
    password="Admin2020!",
    database="lacasadelvitrificado",
    charset="utf8mb4",
)
cur = conn.cursor()
cur.execute(
    """
    UPDATE promotions
    SET status_id = 0,
        is_active = 0,
        updated_date = NOW()
    WHERE status_id = 1 OR is_active = 1
    """
)
print("deactivated:", cur.rowcount)
conn.commit()
cur.execute("SELECT COUNT(*) FROM promotions WHERE status_id = 1 OR is_active = 1")
print("still active:", cur.fetchone()[0])
conn.close()
