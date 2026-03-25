"""
Import du lieu tu CSV files vao PostgreSQL.
Chay script nay tren server sau khi upload CSV files.

Usage: python import_data.py
"""
import csv
import os
import sys

# Fix encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent dir to path for app imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import get_engine, init_db
from sqlalchemy import text

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
EXPORT_DIR = os.path.join(PROJECT_ROOT, 'data', 'export')

# Map table -> columns that should be treated as NULL if empty
NULLABLE_COLUMNS = {
    'gold_prices': ['open', 'high', 'low', 'volume', 'buy_price', 'sell_price'],
    'macro_indicators': ['open', 'high', 'low', 'volume'],
    'news_articles': ['url', 'summary', 'sentiment_score', 'sentiment_label', 'analyzed_at'],
}

def import_table(engine, table_name, csv_path):
    """Import a CSV file into a PostgreSQL table."""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        
        # Skip 'id' column (auto-increment)
        columns_no_id = [c for c in columns if c != 'id']
        
        rows = list(reader)
        if not rows:
            print(f"[SKIP] {table_name}: empty CSV")
            return 0
        
        nullable = NULLABLE_COLUMNS.get(table_name, [])
        
        with engine.begin() as conn:
            # Clear existing data
            conn.execute(text(f"DELETE FROM {table_name}"))
            
            inserted = 0
            for row in rows:
                values = {}
                for col in columns_no_id:
                    val = row[col]
                    if val == '' or val is None:
                        values[col] = None
                    elif col in nullable and val == '':
                        values[col] = None
                    else:
                        values[col] = val
                
                placeholders = ', '.join([f":{c}" for c in columns_no_id])
                col_names = ', '.join(columns_no_id)
                
                conn.execute(
                    text(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"),
                    values
                )
                inserted += 1
            
            print(f"[OK] {table_name}: {inserted} records imported")
            return inserted

def main():
    print(f"[INFO] CSV dir: {os.path.abspath(EXPORT_DIR)}")
    
    if not os.path.exists(EXPORT_DIR):
        print(f"[ERROR] Export dir not found: {EXPORT_DIR}")
        print("[INFO] Upload CSV files sau do chay lai script nay.")
        return
    
    # Initialize DB tables
    init_db()
    engine = get_engine()
    
    total = 0
    for csv_file in sorted(os.listdir(EXPORT_DIR)):
        if not csv_file.endswith('.csv'):
            continue
        
        table_name = csv_file.replace('.csv', '')
        csv_path = os.path.join(EXPORT_DIR, csv_file)
        
        count = import_table(engine, table_name, csv_path)
        total += count
    
    print(f"\n[DONE] Total: {total} records imported")

if __name__ == "__main__":
    main()
