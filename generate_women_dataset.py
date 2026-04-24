"""
generate_women_dataset.py
--------------------------
Run this ONCE from the Smart-Boutique root folder:
    python generate_women_dataset.py

What it does:
    1. Loads cleaned_data.csv
    2. Filters to Women (W) only  →  21,553 rows
    3. Applies all feature engineering (season, age_group, price_per_unit, etc.)
    4. Drops gender column (all W — zero information value)
    5. Saves data/women_cleaned.csv  ← master dataset for ALL ML models

All 4 ML models + the DB seed in main.py will read from this file automatically.
"""

import os
import pandas as pd
import numpy as np
from sklearn.utils import resample

ROOT     = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(ROOT, "data", "cleaned_data.csv")
OUT_PATH = os.path.join(ROOT, "data", "women_cleaned.csv")
BAL_PATH = os.path.join(ROOT, "data", "recommendation_model_data.csv")


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_season(month: int) -> str:
    if month in (3, 4, 5):   return "Spring"
    if month in (6, 7, 8):   return "Summer"
    if month in (9, 10, 11): return "Autumn"
    return "Winter"


def get_age_group(age) -> str:
    try:    age = int(age)
    except: return "Adult"
    if age < 18: return "Teen"
    if age < 30: return "Young Adult"
    if age < 50: return "Adult"
    return "Senior"


def get_amount_bucket(amount) -> str:
    try:    amount = float(amount)
    except: return "Mid"
    if amount <= 400:  return "Low"
    if amount <= 700:  return "Mid"
    if amount <= 1000: return "High"
    return "Premium"


# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading cleaned_data.csv...")
df = pd.read_csv(SRC_PATH)
df.columns = (df.columns.str.strip().str.lower()
              .str.replace(' ', '_').str.replace('-', '_'))
df = df.rename(columns={'channel': 'retail_supplier',
                         'ship-state': 'ship_state',
                         'ship-city':  'ship_city',
                         'ship-postal-code': 'ship_postal_code',
                         'ship-country': 'ship_country'})

print(f"  Total rows: {len(df):,}")

# ── Step 1: Filter Women only ─────────────────────────────────────────────────
gender_map = {'women':'W','woman':'W','female':'W','f':'W',
              'men':'M','man':'M','male':'M','w':'W','m':'M'}
df['gender'] = (df['gender'].astype(str).str.strip().str.lower()
                .map(lambda v: gender_map.get(v, v.upper())))
df = df[df['gender'] == 'W'].copy()
print(f"  After Women filter: {len(df):,} rows")

# ── Step 2: Drop gender column (all W — zero information) ────────────────────
df = df.drop(columns=['gender'], errors='ignore')

# ── Step 3: Drop unused/redundant columns ────────────────────────────────────
drop_cols = ['unnamed:_0', 'unnamed: 0', 'index', 'sku',
             'currency', 'ship_country', 'ship_postal_code']
df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')

# ── Step 4: Type fixes ────────────────────────────────────────────────────────
df['qty']    = pd.to_numeric(df['qty'],    errors='coerce').fillna(1).astype(int)
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype(int)
df['age']    = pd.to_numeric(df['age'],    errors='coerce').fillna(30).astype(int)
df['b2b']    = df['b2b'].astype(str).str.lower().map(
    {'true':1,'1':1,'false':0,'0':0}).fillna(0).astype(int)
df['category'] = df['category'].str.lower().str.strip()
df['size']     = df['size'].str.strip()
df['status']   = df['status'].str.strip()

# ── Step 5: Feature engineering ───────────────────────────────────────────────
df['date']          = pd.to_datetime(df['date'], errors='coerce')
df['month_num']     = df['date'].dt.month.fillna(4).astype(int)
df['season']        = df['month_num'].apply(get_season)
df['weekend_order'] = df['date'].dt.weekday.apply(lambda d: 1 if d >= 5 else 0)
df['age_group']     = df['age'].apply(get_age_group)
df['price_per_unit']= (df['amount'] / df['qty'].replace(0, 1)).round(2)
df['amount_bucket'] = df['amount'].apply(get_amount_bucket)
df['return_flag']   = df['status'].str.lower().isin(
    ['returned', 'cancelled']).astype(int)

# ── Step 6: Clean state names ─────────────────────────────────────────────────
if 'ship_state' in df.columns:
    df['ship_state'] = df['ship_state'].astype(str).str.upper().str.strip()

# ── Step 7: Drop date (not needed for ML, month_num + season capture it) ──────
df = df.drop(columns=['date'], errors='ignore')

# ── Step 8: Final column order ────────────────────────────────────────────────
col_order = [
    'order_id', 'cust_id',
    'age', 'age_group',
    'category', 'size', 'qty', 'amount', 'price_per_unit', 'amount_bucket',
    'retail_supplier', 'b2b',
    'status', 'return_flag',
    'season', 'month_num', 'weekend_order',
    'ship_city', 'ship_state',
]
col_order = [c for c in col_order if c in df.columns]
extra     = [c for c in df.columns if c not in col_order]
df        = df[col_order + extra]

# ── Save women_cleaned.csv ────────────────────────────────────────────────────
df.to_csv(OUT_PATH, index=False)
print(f"\n✅ women_cleaned.csv saved → {OUT_PATH}")
print(f"   Rows    : {len(df):,}")
print(f"   Columns : {len(df.columns)} → {list(df.columns)}")
print(f"   Return rate: {df['return_flag'].mean()*100:.1f}%")
print(f"   Categories: {sorted(df['category'].unique())}")

# ── Save recommendation_model_data.csv (balanced, for ML Model 3) ────────────
print("\nBuilding balanced recommendation dataset...")
cat_counts   = df['category'].value_counts()
target_count = int(cat_counts.quantile(0.75))
print(f"   Target per category: {target_count:,} rows")

chunks = []
for cat in cat_counts.index:
    chunk = df[df['category'] == cat]
    if len(chunk) < target_count:
        chunk = resample(chunk, replace=True,
                         n_samples=target_count, random_state=42)
    chunks.append(chunk)

df_balanced = (pd.concat(chunks)
               .sample(frac=1, random_state=42)
               .reset_index(drop=True))
df_balanced.to_csv(BAL_PATH, index=False)

print(f"✅ recommendation_model_data.csv saved → {BAL_PATH}")
print(f"   Rows    : {len(df_balanced):,}")
print(f"   Category distribution:")
for cat, cnt in df_balanced['category'].value_counts().items():
    print(f"     {cat:20s}: {cnt:,}")

print("\n🎉 Done! Both datasets ready.")
print("   Next: delete .seeded flag and retrain all 4 ML models.")
