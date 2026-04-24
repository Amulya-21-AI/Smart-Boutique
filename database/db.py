"""
Smart-Boutique/database/db.py
"""

import sqlite3
import pandas as pd
import os

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(DATABASE_DIR, "boutique.db")
SCHEMA_PATH  = os.path.join(DATABASE_DIR, "schema.sql")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    conn.close()


def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def run_insert(sql: str, params: tuple = ()) -> int:
    conn = get_connection()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def run_update(sql: str, params: tuple = ()) -> int:
    conn = get_connection()
    cur = conn.execute(sql, params)
    conn.commit()
    rows = cur.rowcount
    conn.close()
    return rows


# ── Customer helpers ──────────────────────────────────────────────────────────
def get_age_group(age: int) -> str:
    if age < 18:  return "Teen"
    if age < 30:  return "Young Adult"
    if age < 50:  return "Adult"
    return "Senior"


def insert_customer(name, email, phone, gender, age,
                    address, city, state, pincode) -> int:
    age_group = get_age_group(int(age))
    return run_insert(
        """INSERT INTO customers
           (name, email, phone, gender, age, age_group,
            address, city, state, pincode)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (name, email, phone, gender, age, age_group,
         address, city, state, pincode)
    )


def get_all_customers() -> pd.DataFrame:
    return run_query("SELECT * FROM customers ORDER BY created_at DESC")


def check_duplicate_customer(phone: str, email: str) -> bool:
    df = run_query(
        "SELECT cust_id FROM customers WHERE phone=? OR (email=? AND email!='')",
        (phone, email)
    )
    return len(df) > 0


# ── Tailor helpers ────────────────────────────────────────────────────────────
def insert_tailor(name, phone, specialty, experience_yrs, joined_date) -> int:
    return run_insert(
        """INSERT INTO tailors (name, phone, specialty, experience_yrs, joined_date)
           VALUES (?,?,?,?,?)""",
        (name, phone, specialty, experience_yrs, joined_date)
    )


def get_all_tailors() -> pd.DataFrame:
    return run_query("SELECT * FROM tailors ORDER BY name")


# ── Order helpers ─────────────────────────────────────────────────────────────
def get_season(date_str: str) -> str:
    try:
        month = int(str(date_str)[5:7])
    except Exception:
        return "Unknown"
    if month in (3, 4, 5):   return "Spring"
    if month in (6, 7, 8):   return "Summer"
    if month in (9, 10, 11): return "Autumn"
    return "Winter"


def get_all_orders() -> pd.DataFrame:
    return run_query("""
        SELECT o.*, c.name AS customer_name, t.name AS tailor_name
        FROM orders o
        LEFT JOIN customers c ON o.cust_id   = c.cust_id
        LEFT JOIN tailors   t ON o.tailor_id = t.tailor_id
        ORDER BY o.order_date DESC
    """)


# ── CSV Seeder ────────────────────────────────────────────────────────────────
def load_csv_to_orders(csv_path: str):
    """
    One-time: load Smart-Boutique/data/cleaned_data.csv into orders table.
    Now also saves gender and age from the CSV.
    """
    df = pd.read_csv(csv_path)

    # Normalise column names
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(' ', '_').str.replace('-', '_'))

    df['order_date'] = pd.to_datetime(
        df.get('date', df.get('order_date', '')), errors='coerce'
    ).dt.strftime('%Y-%m-%d')

    conn = get_connection()
    inserted = 0
    skipped  = 0

    for _, row in df.iterrows():
        try:
            season   = get_season(str(row.get('order_date', '')))
            d        = pd.to_datetime(row.get('order_date'), errors='coerce')
            weekend  = 1 if (not pd.isna(d) and d.weekday() >= 5) else 0
            ret_flag = 1 if str(row.get('status', '')).lower() in (
                           'returned', 'cancelled') else 0

            # gender: normalise W/M
            raw_gender = str(row.get('gender', '')).strip().upper()
            gender_map = {
                'WOMEN': 'W', 'WOMAN': 'W', 'FEMALE': 'W', 'F': 'W',
                'MEN':   'M', 'MAN':   'M', 'MALE':   'M',
                'W': 'W', 'M': 'M'
            }
            gender = gender_map.get(raw_gender, raw_gender)

            # age
            try:
                age = int(row.get('age', 0))
            except Exception:
                age = 0

            conn.execute("""
                INSERT OR IGNORE INTO orders
                (order_id, cust_id, sku, category, size, qty, amount,
                 currency, status, return_flag, order_date, season,
                 weekend_order, gender, age,
                 ship_city, ship_state, ship_postal,
                 ship_country, b2b, retail_supplier)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                str(row.get('order_id', '')),
                int(row.get('cust_id', 0)),
                str(row.get('sku', '')),
                str(row.get('category', '')),
                str(row.get('size', '')),
                int(row.get('qty', 1)),
                float(row.get('amount', 0)),
                str(row.get('currency', 'INR')),
                str(row.get('status', '')),
                ret_flag,
                str(row.get('order_date', '')),
                season,
                weekend,
                gender,
                age,
                str(row.get('ship_city', '')),
                str(row.get('ship_state', '')),
                str(row.get('ship_postal_code', '')),
                str(row.get('ship_country', 'IN')),
                1 if str(row.get('b2b', 'False')).lower() == 'true' else 0,
                str(row.get('retail_supplier', row.get('channel', '')))
            ))
            inserted += 1
        except Exception:
            skipped += 1

    conn.commit()
    conn.close()
    return inserted, skipped
