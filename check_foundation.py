import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv("RDS_HOST"), port=os.getenv("RDS_PORT"),
    dbname=os.getenv("RDS_DATABASE"), user=os.getenv("RDS_USER"),
    password=os.getenv("RDS_PASSWORD"), connect_timeout=10)
cur = conn.cursor()
for t in ["clients", "projects", "consultants", "invoices"]:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"RDS table {t}: {cur.fetchone()[0]} rows")
conn.close()
