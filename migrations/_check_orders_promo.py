import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
import pymysql

conn = pymysql.connect(
    host="31.97.250.169",
    user="admin",
    password="Admin2020!",
    database="lacasadelvitrificado",
    charset="utf8mb4",
)
cur = conn.cursor(pymysql.cursors.DictCursor)
cur.execute("SELECT id, name, promotion_id, status_id, sent_date FROM advertising_campaigns WHERE id IN (27, 28) OR promotion_id IN (18, 19, 12)")
print("lija campaigns:", json.dumps(cur.fetchall(), default=str, ensure_ascii=True))
cur.execute("SELECT COUNT(*) AS n FROM advertising_campaign_deliveries WHERE customer_id=116")
print("deliveries 116:", cur.fetchone())
cur.execute("SELECT status_id FROM sales WHERE id IN (632,633)")
print("sale statuses", cur.fetchall())
conn.close()
