"""
Export du lieu tu SQLite local sang CSV files.
Chay script nay tren may dev, sau do upload CSV len server de import vao PostgreSQL.
"""
import sqlite3
import csv
import os
import sys

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'gold_predictor.db')
EXPORT_DIR = os.path.join(PROJECT_ROOT, 'data', 'export')

# Tables can export (bo predictions va ai_analyses vi se tao moi)
TABLES = ['gold_prices', 'macro_indicators', 'news_articles']

def export_all():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    db_path = os.path.abspath(DB_PATH)
    print(f"[INFO] Database: {db_path}")
    
    if not os.path.exists(db_path):
        print("[ERROR] Khong tim thay database!")
        return
    
    conn = sqlite3.connect(db_path)
    
    for table in TABLES:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print(f"[SKIP] {table}: 0 records")
            continue
        
        cursor = conn.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        csv_path = os.path.join(EXPORT_DIR, f"{table}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        print(f"[OK] {table}: {count} records -> {csv_path}")
    
    conn.close()
    print(f"\n[DONE] Export xong! Files nam trong: {os.path.abspath(EXPORT_DIR)}")

if __name__ == "__main__":
    export_all()
