"""
Smart-Boutique/ML/demand_forecasting.py
-----------------------------------------
ML Model 4 : Seasonal Demand Forecasting
Type        : Time-Series Regression per category
Target      : Units ordered per category per month
Algorithm   : GradientBoostingRegressor   ← upgraded from basic GradientBoosting

IMPROVEMENTS over v1:
    • Expanded feature set: added is_festival_month, peak_season, category_rank
    • Cyclic month encoding preserved (month_sin / month_cos)
    • 3-month rolling average + lag features with proper boundary handling
    • Richer Indian festival calendar (state-level events added)
    • Confidence interval via ± 1.5 × MAE (consistent with v1 but more accurate)
    • GBR tuned: subsample=0.8 + min_samples_leaf=3 reduces overfitting on 96-row dataset
    • Full forecast extended to 12 months (up from 6)

Strategy:
    Data covers Apr–Jun 2022 (3 months). Extended to full 12-month cycle using:
    1. Real observed counts for Apr, May, Jun
    2. Indian fashion seasonal multipliers for remaining 9 months
    3. GradientBoostingRegressor on extended dataset (96 rows = 8 cat × 12 months)
"""

import os, sys, pickle, datetime
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error

MODEL_PATH = os.path.join(ROOT, "ML", "forecast_model.pkl")
META_PATH  = os.path.join(ROOT, "ML", "forecast_model_meta.pkl")
CSV_PATH   = os.path.join(ROOT, "data", "cleaned_data.csv")

CATEGORIES = ['kurta', 'set', 'western dress', 'top',
              'saree', 'blouse', 'ethnic dress', 'bottom']

# ── Indian fashion seasonal multipliers ───────────────────────────────────────
# Index 0 = Jan … 11 = Dec
SEASONAL_PATTERNS = {
    'kurta':         [0.85,0.90,1.10,1.15,1.10,0.85,0.90,1.00,1.10,1.20,1.15,0.90],
    'set':           [0.80,0.85,1.05,1.15,1.10,0.80,0.95,1.10,1.15,1.25,1.20,1.00],
    'western dress': [0.90,1.10,1.05,0.95,1.00,0.85,0.90,0.95,1.00,1.10,1.15,1.20],
    'saree':         [1.00,0.90,1.10,1.05,0.90,0.85,1.00,1.10,1.20,1.30,1.25,1.10],
    'top':           [0.85,1.00,1.05,1.10,1.05,0.85,0.90,0.95,1.00,1.05,1.10,1.00],
    'blouse':        [1.00,0.90,1.05,1.00,0.90,0.85,1.00,1.10,1.20,1.25,1.20,1.05],
    'ethnic dress':  [0.90,0.90,1.00,1.05,1.00,0.85,0.90,1.05,1.15,1.25,1.20,1.05],
    'bottom':        [0.90,0.95,1.00,1.05,1.00,0.85,0.90,0.95,1.00,1.05,1.00,0.90],
}

# Category rank by overall volume (higher = more popular = higher base demand)
CATEGORY_RANK = {cat: i for i, cat in enumerate(
    ['set', 'kurta', 'western dress', 'top', 'saree', 'ethnic dress', 'blouse', 'bottom'])}

# Indian festival calendar — month → list of festivals
FESTIVALS = {
    1:  ['Pongal', 'Makar Sankranti', 'Republic Day'],
    2:  ["Valentine's Day", 'Maha Shivratri'],
    3:  ['Holi', 'Ugadi', 'Baisakhi'],
    4:  ['Ram Navami', 'Eid al-Fitr'],
    5:  ["Mother's Day", 'Buddha Purnima'],
    6:  ['Eid al-Adha', 'Jagannath Rath Yatra'],
    7:  ['Muharram', 'Guru Purnima'],
    8:  ['Independence Day', 'Raksha Bandhan', 'Janmashtami'],
    9:  ['Ganesh Chaturthi', 'Onam', 'Navratri'],
    10: ['Navratri', 'Dussehra', 'Karwa Chauth'],
    11: ['Diwali', 'Bhai Dooj', 'Chhath Puja'],
    12: ['Christmas', 'New Year Eve'],
}

# Peak shopping months (Oct-Nov heavy festivals)
PEAK_MONTHS = {10, 11, 9}

MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']
SEASONS_MAP = {
    1:'Winter',2:'Winter',3:'Spring',4:'Spring',5:'Spring',
    6:'Summer',7:'Summer',8:'Summer',9:'Autumn',10:'Autumn',
    11:'Autumn',12:'Winter',
}

FEATURE_COLS = [
    'month', 'month_sin', 'month_cos', 'season_enc', 'cat_enc',
    'category_rank', 'seasonal_index', 'lag_1', 'lag_2',
    'rolling_3', 'festivals', 'is_festival_month', 'is_peak_season',
]


# ── Build training dataset ────────────────────────────────────────────────────
def build_full_year_data(real_monthly: dict) -> pd.DataFrame:
    """Build full 12-month × 8-category dataset, blending real + simulated."""
    np.random.seed(42)
    rows = []
    for cat in CATEGORIES:
        base_vals = []
        for m, cat_counts in real_monthly.items():
            if cat in cat_counts:
                mult = SEASONAL_PATTERNS[cat][m - 1]
                if mult > 0:
                    base_vals.append(cat_counts[cat] / mult)
        base = np.mean(base_vals) if base_vals else 500

        for month in range(1, 13):
            mult  = SEASONAL_PATTERNS[cat][month - 1]
            if month in real_monthly and cat in real_monthly[month]:
                units = real_monthly[month][cat]
            else:
                noise = np.random.randint(-30, 30)
                units = max(5, int(base * mult) + noise)

            rows.append({
                'month':             month,
                'month_name':        MONTH_NAMES[month - 1],
                'season':            SEASONS_MAP[month],
                'category':          cat,
                'units':             units,
                'is_real':           month in real_monthly,
                'festivals':         len(FESTIVALS.get(month, [])),
                'is_festival_month': 1 if len(FESTIVALS.get(month, [])) >= 2 else 0,
                'is_peak_season':    1 if month in PEAK_MONTHS else 0,
            })
    return pd.DataFrame(rows)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all ML feature columns."""
    df = df.copy()
    df['season_enc']     = df['season'].map(
        {'Winter':0,'Spring':1,'Summer':2,'Autumn':3})
    df['cat_enc']        = df['category'].map(
        {c: i for i, c in enumerate(CATEGORIES)})
    df['category_rank']  = df['category'].map(CATEGORY_RANK).fillna(7)
    df['month_sin']      = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos']      = np.cos(2 * np.pi * df['month'] / 12)
    df['seasonal_index'] = df.apply(
        lambda r: SEASONAL_PATTERNS.get(r['category'], [1]*12)[r['month']-1], axis=1)

    df = df.sort_values(['category', 'month']).copy()
    df['lag_1']     = df.groupby('category')['units'].shift(1).fillna(df['units'])
    df['lag_2']     = df.groupby('category')['units'].shift(2).fillna(df['units'])
    df['rolling_3'] = (df.groupby('category')['units']
                         .transform(lambda x: x.rolling(3, min_periods=1).mean()))
    return df


# ── Load real monthly data ────────────────────────────────────────────────────
def load_real_monthly() -> dict:
    try:
        from database.db import run_query
        df = run_query("""
            SELECT CAST(strftime('%m', order_date) AS INTEGER) AS month,
                   category, COUNT(*) AS units
            FROM orders
            WHERE order_date IS NOT NULL AND category IS NOT NULL
            GROUP BY month, category
        """)
        if len(df) > 0:
            result = {}
            for _, row in df.iterrows():
                m   = int(row['month'])
                cat = row['category']
                result.setdefault(m, {})[cat] = int(row['units'])
            print(f"   ✅ Real data from DB: {len(result)} months")
            return result
    except Exception as e:
        print(f"   DB error ({e}) — using CSV")

    df = pd.read_csv(CSV_PATH)
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(' ', '_').str.replace('-', '_'))
    df['date']  = pd.to_datetime(df.get('date', ''), errors='coerce')
    df['month'] = df['date'].dt.month

    result = {}
    for (month, cat), group in df.groupby(['month', 'category']):
        result.setdefault(int(month), {})[str(cat)] = len(group)

    print(f"   ✅ Real data from CSV: months {sorted(result.keys())}")
    return result


# ── Train ─────────────────────────────────────────────────────────────────────
def train_model() -> dict:
    print("📊 Loading historical data...")
    real_monthly = load_real_monthly()

    print("🔧 Building full-year training dataset...")
    df = build_full_year_data(real_monthly)
    df = add_features(df)
    print(f"   Training rows: {len(df)} ({len(CATEGORIES)} categories × 12 months)")

    X = df[FEATURE_COLS]
    y = df['units']

    print("🤖 Training Gradient Boosting Regressor...")
    model = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=3,
        random_state=42,
    )
    model.fit(X, y)

    cv_mae  = -cross_val_score(model, X, y,
                                scoring='neg_mean_absolute_error', cv=3).mean()
    y_pred  = model.predict(X)
    mae     = mean_absolute_error(y, y_pred)

    fi = pd.Series(model.feature_importances_,
                   index=FEATURE_COLS).sort_values(ascending=False)
    cat_totals    = df.groupby('category')['units'].sum().to_dict()
    monthly_totals= df.groupby('month')['units'].sum().to_dict()
    peak_months   = {
        cat: int(df[df['category'] == cat].nlargest(1, 'units')['month'].iloc[0])
        for cat in CATEGORIES
    }

    metrics = {
        'mae':               round(mae, 1),
        'cv_mae':            round(cv_mae, 1),
        'total_rows':        len(df),
        'categories':        CATEGORIES,
        'real_months':       sorted(real_monthly.keys()),
        'cat_totals':        cat_totals,
        'monthly_totals':    monthly_totals,
        'feature_importance':fi.to_dict(),
        'peak_months':       peak_months,
        'algorithm':         'GradientBoostingRegressor v2.0',
    }

    meta = {
        'model':         model,
        'metrics':       metrics,
        'full_year_df':  df,
        'real_monthly':  real_monthly,
        'feature_cols':  FEATURE_COLS,
        'categories':    CATEGORIES,
    }
    with open(MODEL_PATH, 'wb') as f: pickle.dump(model, f)
    with open(META_PATH,  'wb') as f: pickle.dump(meta,  f)

    print(f"\n✅ Model saved!")
    print(f"   MAE    : {mae:.1f} units")
    print(f"   CV MAE : {cv_mae:.1f} units")
    return metrics


# ── Forecast ──────────────────────────────────────────────────────────────────
def forecast_next_months(n_months: int = 6,
                          start_month: int = None) -> pd.DataFrame:
    """
    Forecast demand for the next n_months (max 12).

    Returns DataFrame: month, month_name, category, forecast_units,
                       lower_bound, upper_bound, season, festivals
    """
    if not os.path.exists(META_PATH):
        return pd.DataFrame()

    with open(META_PATH, 'rb') as f: meta = pickle.load(f)
    model   = meta['model']
    full_df = meta['full_year_df']

    if start_month is None:
        start_month = datetime.date.today().month

    mae  = meta['metrics']['mae']
    rows = []

    for i in range(min(n_months, 12)):
        month = ((start_month - 1 + i) % 12) + 1

        for cat in CATEGORIES:
            cat_df   = full_df[full_df['category'] == cat].sort_values('month')
            lag_vals = cat_df['units'].values

            lag_1    = float(lag_vals[(month - 2) % 12])
            lag_2    = float(lag_vals[(month - 3) % 12])
            rolling3 = float(np.mean(lag_vals[max(0, month-3):month]))

            features = pd.DataFrame([{
                'month':            month,
                'month_sin':        np.sin(2 * np.pi * month / 12),
                'month_cos':        np.cos(2 * np.pi * month / 12),
                'season_enc':       {'Winter':0,'Spring':1,'Summer':2,'Autumn':3}
                                     [SEASONS_MAP[month]],
                'cat_enc':          CATEGORIES.index(cat),
                'category_rank':    CATEGORY_RANK.get(cat, 7),
                'seasonal_index':   SEASONAL_PATTERNS[cat][month - 1],
                'lag_1':            lag_1,
                'lag_2':            lag_2,
                'rolling_3':        rolling3,
                'festivals':        len(FESTIVALS.get(month, [])),
                'is_festival_month':1 if len(FESTIVALS.get(month, [])) >= 2 else 0,
                'is_peak_season':   1 if month in PEAK_MONTHS else 0,
            }])

            pred  = float(model.predict(features)[0])
            lower = max(0, pred - mae * 1.5)
            upper = pred + mae * 1.5

            rows.append({
                'month':          month,
                'month_name':     MONTH_NAMES[month - 1],
                'season':         SEASONS_MAP[month],
                'category':       cat,
                'forecast_units': round(pred),
                'lower_bound':    round(lower),
                'upper_bound':    round(upper),
                'festivals':      ', '.join(FESTIVALS.get(month, [])),
                'seasonal_index': SEASONAL_PATTERNS[cat][month - 1],
                'is_peak_season': month in PEAK_MONTHS,
            })

    return pd.DataFrame(rows)


def get_full_year_actuals() -> pd.DataFrame:
    if not os.path.exists(META_PATH):
        return pd.DataFrame()
    with open(META_PATH, 'rb') as f: meta = pickle.load(f)
    return meta['full_year_df']


def get_restock_alerts(forecast_df: pd.DataFrame,
                        threshold_pct: float = 0.20) -> pd.DataFrame:
    """Flag categories with demand spike > threshold_pct next month."""
    if forecast_df.empty:
        return pd.DataFrame()

    curr_month = datetime.date.today().month
    next_month = (curr_month % 12) + 1

    curr = (forecast_df[forecast_df['month'] == curr_month]
            [['category','forecast_units']]
            .rename(columns={'forecast_units':'current'}))
    nxt  = (forecast_df[forecast_df['month'] == next_month]
            [['category','forecast_units']]
            .rename(columns={'forecast_units':'next_month'}))

    merged = curr.merge(nxt, on='category')
    merged['change_pct'] = ((merged['next_month'] - merged['current'])
                             / merged['current'].replace(0, 1) * 100).round(1)
    merged['alert'] = merged['change_pct'].apply(
        lambda x: '🔴 Stock Up!' if x > threshold_pct * 100
                  else '🟡 Watch' if x > 0
                  else '🟢 Stable')
    return merged.sort_values('change_pct', ascending=False)


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    metrics = train_model()
    print("\n📈 Results:")
    for k, v in metrics.items():
        if k not in ('feature_importance','cat_totals',
                     'monthly_totals','peak_months'):
            print(f"   {k}: {v}")
    print("\n🔍 Feature Importance:")
    for feat, score in sorted(metrics['feature_importance'].items(),
                               key=lambda x: x[1], reverse=True):
        print(f"   {feat:20s} {'█'*int(score*40)} {score:.4f}")
    print("\n📅 6-Month Forecast:")
    fc = forecast_next_months(6)
    summary = fc.groupby('month_name')['forecast_units'].sum()
    for m, v in summary.items():
        print(f"   {m}: {int(v):,} total units")
    print("\n🚨 Restock Alerts:")
    alerts = get_restock_alerts(fc)
    for _, row in alerts.iterrows():
        print(f"   {row['category']:15s} {row['alert']} ({row['change_pct']:+.1f}%)")
