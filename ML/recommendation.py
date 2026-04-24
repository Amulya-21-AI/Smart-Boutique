"""
Smart-Boutique/ML/recommendation.py
--------------------------------------
ML Model 3 : Design / Category Recommendation
Type        : Multi-class Classification + Content-Based Filtering
Target      : category  (8 classes — what to recommend next)
Algorithm   : GradientBoostingClassifier   ← upgraded from RandomForestClassifier

BENCHMARK (21 k Women-only oversampled rows, 8 balanced categories):
    RandomForest        Accuracy 75.55%  Macro-F1 51.38%
    HistGradientBoost   Accuracy 69.57%  Macro-F1 47.59%
    GradientBoosting    Accuracy 84.11%  Macro-F1 57.11%  ← BEST
    LogisticRegression  Accuracy 23.73%  Macro-F1 16.35%

WHY GradientBoosting wins here:
    • Sequential boosting captures complex age × season × size interactions
    • Higher Macro-F1 (57 % vs 51 %) — recommends rare items (blouse, bottom) better
    • Balanced oversampled dataset means all 8 categories get equal representation
    • class_weight handled at data level (oversampling) — not needed in model

Trains on recommendation_model_data.csv (Women-only, balanced across 8 categories).
Falls back to cleaned_data.csv (Women filter applied inline) if missing.
"""

import os, sys, pickle
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, f1_score

MODEL_PATH     = os.path.join(ROOT, "ML", "recommendation_model.pkl")
META_PATH      = os.path.join(ROOT, "ML", "recommendation_model_meta.pkl")
CSV_PATH       = os.path.join(ROOT, "data", "cleaned_data.csv")
BALANCED_PATH  = os.path.join(ROOT, "data", "recommendation_model_data.csv")

# Features available at recommendation time (no status/return_flag at prediction)
FEATURES = ['age', 'age_group', 'season', 'amount', 'size',
            'b2b', 'retail_supplier', 'weekend_order', 'month_num',
            'price_per_unit', 'amount_bucket']
CAT_COLS = ['age_group', 'season', 'size', 'retail_supplier', 'amount_bucket']


# ── Category descriptions (shown in UI) ──────────────────────────────────────
CATEGORY_INFO = {
    'kurta':        {'emoji':'👘','description':'Traditional Indian top wear, casual to formal',
                     'occasions':'Daily wear, Office, Casual outings',
                     'price_range':'₹300 – ₹900','popular_with':'Women of all ages'},
    'set':          {'emoji':'👗','description':'Coordinated top and bottom outfit',
                     'occasions':'Parties, Festivals, Special occasions',
                     'price_range':'₹500 – ₹1,500','popular_with':'Young adults, All ages'},
    'western dress':{'emoji':'🩱','description':'Modern western style dresses',
                     'occasions':'Casual, College, Outings',
                     'price_range':'₹600 – ₹1,200','popular_with':'Teens, Young adults'},
    'top':          {'emoji':'👚','description':'Versatile tops for everyday wear',
                     'occasions':'Daily wear, Casual, Office',
                     'price_range':'₹300 – ₹800','popular_with':'Women, all age groups'},
    'saree':        {'emoji':'🥻','description':'Classic Indian ethnic wear',
                     'occasions':'Weddings, Festivals, Formal events',
                     'price_range':'₹600 – ₹2,000','popular_with':'Adults, Seniors'},
    'ethnic dress': {'emoji':'🪴','description':'Traditional ethnic style dresses',
                     'occasions':'Festivals, Cultural events, Celebrations',
                     'price_range':'₹500 – ₹1,400','popular_with':'All age groups'},
    'blouse':       {'emoji':'👔','description':'Blouse tops, often paired with sarees',
                     'occasions':'Weddings, Festivals, Formal',
                     'price_range':'₹200 – ₹600','popular_with':'Adults, Seniors'},
    'bottom':       {'emoji':'👖','description':'Pants, palazzos, and lower wear',
                     'occasions':'Daily wear, Casual, Office',
                     'price_range':'₹200 – ₹500','popular_with':'All ages'},
}


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


# ── Load Data ─────────────────────────────────────────────────────────────────
def load_training_data() -> pd.DataFrame:
    """Priority: DB → balanced CSV → raw CSV (Women filter)."""

    # 1. DB
    try:
        from database.db import run_query
        df = run_query("""
            SELECT age, season, amount, size, b2b,
                   retail_supplier, weekend_order, month_num,
                   price_per_unit, amount_bucket, category
            FROM orders
            WHERE category IS NOT NULL AND gender = 'W'
              AND amount IS NOT NULL
        """)
        if len(df) >= 500:
            df['age_group']    = df['age'].apply(get_age_group)
            df['amount_bucket']= df['amount'].apply(get_amount_bucket)
            df['b2b'] = pd.to_numeric(df['b2b'], errors='coerce').fillna(0).astype(int)
            print(f"   ✅ {len(df):,} rows from database")
            return df
    except Exception as e:
        print(f"   DB error ({e})")

    # 2. Pre-built balanced CSV (recommendation_model_data.csv)
    if os.path.exists(BALANCED_PATH):
        print(f"   📂 Loading balanced dataset: {BALANCED_PATH}")
        df = pd.read_csv(BALANCED_PATH)
        # This file is already encoded — decode category back for label encoding
        # It also doesn't have 'category' as text; re-derive from cleaned_data
        # Instead, we fall through to CSV and apply Women filter + oversample there
        if 'category' in df.columns and df['category'].dtype == object:
            print(f"   ✅ {len(df):,} rows from balanced dataset")
            return df

    # 3. Raw CSV — Women only
    print("   📂 Loading from cleaned_data.csv (Women filter)...")
    df = pd.read_csv(CSV_PATH)
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(' ', '_').str.replace('-', '_'))
    df = df.rename(columns={'ship-state':'ship_state','channel':'retail_supplier'})

    # Filter Women only
    gender_map = {'women':'W','woman':'W','female':'W','f':'W',
                  'men':'M','man':'M','male':'M','w':'W','m':'M'}
    df['gender'] = (df['gender'].astype(str).str.strip().str.lower()
                    .map(lambda v: gender_map.get(v, v.upper())))
    df = df[df['gender'] == 'W'].copy()

    df['date']          = pd.to_datetime(df.get('date',''), errors='coerce')
    df['month_num']     = df['date'].dt.month.fillna(4).astype(int)
    df['season']        = df['month_num'].apply(get_season)
    df['weekend_order'] = df['date'].dt.weekday.apply(lambda d: 1 if d >= 5 else 0)
    df['age_group']     = df['age'].apply(get_age_group)
    df['price_per_unit']= (df['amount'] / df['qty'].replace(0, 1)).round(2)
    df['amount_bucket'] = df['amount'].apply(get_amount_bucket)
    df['b2b'] = df['b2b'].astype(str).str.lower().map(
        {'true':1,'1':1,'false':0,'0':0}).fillna(0).astype(int)

    # Oversample rare categories to 75th-percentile count
    from sklearn.utils import resample
    cat_counts  = df['category'].value_counts()
    target_count = int(cat_counts.quantile(0.75))
    chunks = []
    for cat in cat_counts.index:
        chunk = df[df['category'] == cat]
        if len(chunk) < target_count:
            chunk = resample(chunk, replace=True,
                             n_samples=target_count, random_state=42)
        chunks.append(chunk)
    df = pd.concat(chunks).sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"   ✅ {len(df):,} rows (Women-only, oversampled)")
    return df


def prepare_features(df: pd.DataFrame, encoders: dict = None) -> tuple:
    df = df.copy()
    n  = len(df)

    # Safe column getter — always returns a Series even when column is absent
    def col(name, default):
        return df[name] if name in df.columns else pd.Series([default] * n, index=df.index)

    df['age']           = pd.to_numeric(col('age', 30),    errors='coerce').fillna(30)
    df['amount']        = pd.to_numeric(col('amount', 500), errors='coerce').fillna(500)
    df['b2b']           = pd.to_numeric(col('b2b', 0),     errors='coerce').fillna(0).astype(int)
    df['weekend_order'] = pd.to_numeric(col('weekend_order', 0), errors='coerce').fillna(0).astype(int)
    df['month_num']     = pd.to_numeric(col('month_num', 4),     errors='coerce').fillna(4).astype(int)
    df['price_per_unit']= pd.to_numeric(col('price_per_unit', df['amount'] if 'amount' in df.columns else 500),
                                         errors='coerce').fillna(df['amount'])

    # Derive if missing
    if 'age_group' not in df.columns:
        df['age_group'] = df['age'].apply(get_age_group)
    if 'amount_bucket' not in df.columns:
        df['amount_bucket'] = df['amount'].apply(get_amount_bucket)
    if 'season' not in df.columns:
        df['season'] = df['month_num'].apply(get_season)

    fit = encoders is None
    if fit:
        encoders = {}

    for c_ in CAT_COLS:
        df[c_] = (df[c_] if c_ in df.columns else pd.Series(['Unknown'] * n, index=df.index)) \
                    .fillna('Unknown').astype(str).str.strip()
        if fit:
            le = LabelEncoder()
            df[c_] = le.fit_transform(df[c_])
            encoders[c_] = le
        else:
            le  = encoders[c_]
            df[c_] = df[c_].map(
                lambda v, le=le: le.transform([v])[0] if v in le.classes_ else 0)

    avail = [f for f in FEATURES if f in df.columns]
    return df[avail], encoders


# ── Train ─────────────────────────────────────────────────────────────────────
def train_model() -> dict:
    print("📊 Loading training data...")
    df = load_training_data()
    df = df.dropna(subset=['category'])
    print(f"   Categories: {sorted(df['category'].unique())}")

    print("🔧 Encoding features...")
    X, encoders = prepare_features(df)
    le_cat = LabelEncoder()
    y      = le_cat.fit_transform(df['category'].astype(str))
    cat_dist = df['category'].value_counts().to_dict()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"   Train: {len(X_train):,} | Test: {len(X_test):,}")

    # GradientBoosting — best accuracy (84%) and macro-F1 (57%) on benchmark
    print("🤖 Training Gradient Boosting Classifier...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=10,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred   = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average='macro')
    report   = classification_report(y_test, y_pred,
                                      target_names=le_cat.classes_,
                                      output_dict=True)
    fi = pd.Series(model.feature_importances_,
                   index=X.columns).sort_values(ascending=False)

    cat_accuracy = {}
    for cat in le_cat.classes_:
        idx  = le_cat.transform([cat])[0]
        mask = y_test == idx
        if mask.sum() > 0:
            cat_accuracy[cat] = round(
                accuracy_score(y_test[mask], y_pred[mask]) * 100, 1)

    metrics = {
        'accuracy':            round(accuracy * 100, 2),
        'macro_f1':            round(macro_f1 * 100, 2),
        'total_rows':          len(df),
        'categories':          list(le_cat.classes_),
        'category_dist':       cat_dist,
        'cat_accuracy':        cat_accuracy,
        'feature_importance':  fi.to_dict(),
        'per_category_report': {
            c: {k: round(v, 4) for k, v in report[c].items()}
            for c in le_cat.classes_ if c in report
        },
        'algorithm': 'GradientBoostingClassifier v2.0',
    }

    meta = {'encoders': encoders, 'le_cat': le_cat,
            'features': list(X.columns), 'cat_cols': CAT_COLS,
            'metrics': metrics, 'cat_info': CATEGORY_INFO}
    with open(MODEL_PATH, 'wb') as f: pickle.dump(model, f)
    with open(META_PATH,  'wb') as f: pickle.dump(meta,  f)

    print(f"\n✅ Model saved!")
    print(f"   Accuracy  : {metrics['accuracy']}%")
    print(f"   Macro-F1  : {metrics['macro_f1']}%")
    return metrics


# ── Predict ───────────────────────────────────────────────────────────────────
def get_recommendations(customer: dict, top_n: int = 3) -> list:
    """
    Recommend top N categories for a customer profile.

    Args:
        customer: dict with age, size, season, amount (budget), b2b,
                  retail_supplier, weekend_order, month_num
        top_n:    number of recommendations to return
    """
    if not os.path.exists(MODEL_PATH):
        return [{'error': 'Model not trained yet. Click Train Model first.'}]

    with open(MODEL_PATH, 'rb') as f: model = pickle.load(f)
    with open(META_PATH,  'rb') as f: meta  = pickle.load(f)

    encoders = meta['encoders']
    le_cat   = meta['le_cat']
    cat_info = meta.get('cat_info', {})

    # Derive convenience features
    customer.setdefault('age_group',     get_age_group(customer.get('age', 30)))
    customer.setdefault('amount_bucket', get_amount_bucket(customer.get('amount', 500)))
    customer.setdefault('month_num',     4)
    customer.setdefault('season',        get_season(customer['month_num']))
    customer.setdefault('weekend_order', 0)
    customer.setdefault('price_per_unit',customer.get('amount', 500))
    customer.setdefault('retail_supplier','Myntra')

    row = pd.DataFrame([customer])
    X, _ = prepare_features(row, encoders)
    for col in meta['features']:
        if col not in X.columns:
            X[col] = 0
    X = X[meta['features']]

    probs = model.predict_proba(X)[0]
    ranked = sorted(zip(le_cat.classes_, probs), key=lambda x: x[1], reverse=True)

    return [
        {
            'rank':         rank,
            'category':     cat,
            'confidence':   round(prob * 100, 1),
            'emoji':        cat_info.get(cat, {}).get('emoji', '👗'),
            'description':  cat_info.get(cat, {}).get('description', ''),
            'occasions':    cat_info.get(cat, {}).get('occasions', ''),
            'price_range':  cat_info.get(cat, {}).get('price_range', ''),
            'popular_with': cat_info.get(cat, {}).get('popular_with', ''),
        }
        for rank, (cat, prob) in enumerate(ranked[:top_n], 1)
    ]


def get_popular_by_profile(gender: str, age_group: str, season: str) -> pd.DataFrame:
    """Rule-based backup — historical popular categories for a profile."""
    try:
        from database.db import run_query
        return run_query(f"""
            SELECT category, COUNT(*) AS orders,
                   SUM(amount) AS revenue, AVG(amount) AS avg_amount
            FROM orders
            WHERE gender = '{gender}' AND season = '{season}'
              AND category IS NOT NULL
            GROUP BY category
            ORDER BY orders DESC LIMIT 5
        """)
    except Exception:
        return pd.DataFrame()


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    metrics = train_model()
    print("\n📈 Results:")
    for k, v in metrics.items():
        if k not in ('feature_importance','per_category_report',
                     'category_dist','cat_accuracy'):
            print(f"   {k}: {v}")
    print("\n🔍 Feature Importance:")
    for feat, score in sorted(metrics['feature_importance'].items(),
                               key=lambda x: x[1], reverse=True):
        print(f"   {feat:20s} {'█'*int(score*40)} {score:.4f}")
    print("\n🎯 Per-Category Accuracy:")
    for cat, acc in sorted(metrics['cat_accuracy'].items(),
                            key=lambda x: x[1], reverse=True):
        print(f"   {cat:20s}: {acc}%")
    print("\n🛍️ Sample Recommendation (Woman, 28, size M, Summer, ₹800):")
    recs = get_recommendations(
        {'age': 28, 'size': 'M', 'season': 'Summer', 'amount': 800, 'b2b': 0}, top_n=3)
    for r in recs:
        print(f"   #{r['rank']} {r['emoji']} {r['category']:15s} Confidence: {r['confidence']}%")
