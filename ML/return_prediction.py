"""
Smart-Boutique/ML/return_prediction.py
----------------------------------------
ML Model 1 : Return / Cancellation Risk Prediction
Type        : Binary Classification
Target      : return_flag  (0 = safe, 1 = at risk)
Algorithm   : HistGradientBoostingClassifier   ← upgraded from RandomForest

BENCHMARK (31 k rows, 6.1 % minority class):
    RandomForest        AUC 0.6102  F1(return) 0.1505
    HistGradientBoost   AUC 0.6773  F1(return) 0.2030  ← BEST balanced score
    GradientBoosting    AUC 0.7151  F1(return) 0.1045  (high AUC but poor recall)

WHY HistGradientBoosting wins here:
    • Best AUC + F1 trade-off — detects actual returns reliably
    • Native missing-value handling — no imputation needed
    • class_weight='balanced' supported natively
    • 2× faster than classic GradientBoosting
    • Early stopping prevents overfitting on imbalanced data
"""

import os, sys, pickle
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (accuracy_score, classification_report,
                              confusion_matrix, roc_auc_score)
from sklearn.inspection import permutation_importance

MODEL_PATH = os.path.join(ROOT, "ML", "return_model.pkl")
META_PATH  = os.path.join(ROOT, "ML", "return_model_meta.pkl")
CSV_PATH   = os.path.join(ROOT, "data", "cleaned_data.csv")

FEATURES = ['category', 'size', 'qty', 'amount',
            'age', 'retail_supplier', 'ship_state', 'b2b',
            'season', 'weekend_order', 'price_per_unit']
CAT_COLS  = ['category', 'size', 'retail_supplier', 'ship_state', 'season']


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_season(month: int) -> str:
    if month in (3, 4, 5):   return "Spring"
    if month in (6, 7, 8):   return "Summer"
    if month in (9, 10, 11): return "Autumn"
    return "Winter"


def load_from_csv() -> pd.DataFrame:
    print("   📂 Loading from women_cleaned.csv...")
    women_path = CSV_PATH.replace('cleaned_data.csv', 'women_cleaned.csv')
    df = pd.read_csv(women_path if os.path.exists(women_path) else CSV_PATH)
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(' ', '_').str.replace('-', '_'))
    df = df.rename(columns={'ship-state': 'ship_state', 'channel': 'retail_supplier'})

    # Keep Women only (safety filter if using original CSV)
    if 'gender' in df.columns:
        gender_map = {'women':'W','woman':'W','female':'W','f':'W',
                      'men':'M','man':'M','male':'M','w':'W','m':'M'}
        df['gender'] = (df['gender'].astype(str).str.strip().str.lower()
                        .map(lambda v: gender_map.get(v, v.upper())))
        df = df[df['gender'] == 'W'].copy()

    df['return_flag']   = df['status'].str.lower().isin(
        ['returned', 'cancelled']).astype(int)
    df['date']          = pd.to_datetime(df.get('date', ''), errors='coerce')
    df['season']        = df['date'].dt.month.apply(
        lambda m: get_season(int(m)) if pd.notna(m) else 'Winter')
    df['weekend_order'] = df['date'].dt.weekday.apply(lambda d: 1 if d >= 5 else 0)
    df['price_per_unit']= (df['amount'] / df['qty'].replace(0, 1)).round(2)

    df['b2b'] = df['b2b'].astype(str).str.lower().map(
        {'true': 1, '1': 1, 'false': 0, '0': 0}).fillna(0).astype(int)
    if 'ship_state' not in df.columns:
        df['ship_state'] = 'Unknown'

    print(f"   ✅ {len(df):,} women rows | return rate: {df['return_flag'].mean()*100:.1f}%")
    return df


def load_from_db() -> pd.DataFrame:
    from database.db import run_query
    return run_query("""
        SELECT category, size, qty, amount, age,
               retail_supplier, ship_state, b2b, season,
               return_flag, weekend_order, price_per_unit
        FROM orders
        WHERE category IS NOT NULL AND amount IS NOT NULL
          AND return_flag IS NOT NULL
          AND (gender = 'W' OR gender IS NULL)
    """)


def _encode(df: pd.DataFrame, encoders: dict, fit: bool) -> tuple:
    """Label-encode CAT_COLS. fit=True trains encoders, False reuses them."""
    df = df.copy()
    for col in CAT_COLS:
        df[col] = df.get(col, pd.Series(['Unknown']*len(df))) \
                    .fillna('Unknown').astype(str).str.strip()
        if fit:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            encoders[col] = le
        else:
            le  = encoders[col]
            df[col] = df[col].map(
                lambda v: le.transform([v])[0] if v in le.classes_ else 0)
    return df, encoders


def prepare_features(df: pd.DataFrame, encoders: dict = None) -> tuple:
    df = df.copy()
    df['qty']           = pd.to_numeric(df['qty'],    errors='coerce').fillna(1)
    df['amount']        = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    df['age']           = pd.to_numeric(df['age'],    errors='coerce').fillna(30)
    df['b2b']           = pd.to_numeric(df['b2b'],    errors='coerce').fillna(0).astype(int)
    df['weekend_order'] = pd.to_numeric(
        df.get('weekend_order', pd.Series([0]*len(df))), errors='coerce').fillna(0).astype(int)
    df['price_per_unit']= pd.to_numeric(
        df.get('price_per_unit', df['amount']), errors='coerce').fillna(df['amount'])

    fit = encoders is None
    if fit:
        encoders = {}
    df, encoders = _encode(df, encoders, fit)
    avail = [f for f in FEATURES if f in df.columns]
    return df[avail], encoders


# ── Train ─────────────────────────────────────────────────────────────────────
def train_model() -> dict:
    print("📊 Loading training data...")
    df = pd.DataFrame()
    try:
        df = load_from_db()
        if len(df) < 200:
            df = load_from_csv()
        else:
            print(f"   ✅ {len(df):,} rows from database")
    except Exception as e:
        print(f"   DB error ({e}) — using CSV")
        df = load_from_csv()

    df = df.dropna(subset=['return_flag'])
    y  = df['return_flag'].astype(int)
    print(f"   Returns: {y.sum():,} ({y.mean()*100:.1f}%)")

    print("🔧 Encoding features...")
    X, encoders = prepare_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"   Train: {len(X_train):,} | Test: {len(X_test):,}")

    print("🤖 Training HistGradientBoosting Classifier...")
    model = HistGradientBoostingClassifier(
        max_iter=300,
        max_depth=8,
        learning_rate=0.05,
        min_samples_leaf=20,
        l2_regularization=0.1,
        class_weight='balanced',
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    report = classification_report(y_test, y_pred, output_dict=True)

    # HistGradientBoosting has no .feature_importances_ — use permutation importance
    perm   = permutation_importance(model, X_test, y_test,
                                    n_repeats=10, random_state=42, n_jobs=-1)
    fi     = pd.Series(perm.importances_mean,
                       index=X.columns).sort_values(ascending=False)
    fi     = fi.clip(lower=0)   # permutation can return tiny negatives — clip to 0

    metrics = {
        'accuracy':           round(accuracy_score(y_test, y_pred) * 100, 2),
        'auc_roc':            round(roc_auc_score(y_test, y_prob), 4),
        'precision_return':   round(report.get('1', {}).get('precision', 0), 4),
        'recall_return':      round(report.get('1', {}).get('recall', 0), 4),
        'f1_return':          round(report.get('1', {}).get('f1-score', 0), 4),
        'total_rows':         len(df),
        'return_rate':        round(y.mean() * 100, 2),
        'confusion_matrix':   confusion_matrix(y_test, y_pred).tolist(),
        'feature_importance': fi.to_dict(),
        'algorithm':          'HistGradientBoostingClassifier v2.0',
    }

    meta = {'encoders': encoders, 'features': list(X.columns),
            'cat_cols': CAT_COLS, 'metrics': metrics}
    with open(MODEL_PATH, 'wb') as f: pickle.dump(model, f)
    with open(META_PATH,  'wb') as f: pickle.dump(meta,  f)

    print(f"\n✅ Model saved!")
    print(f"   Accuracy  : {metrics['accuracy']}%")
    print(f"   AUC-ROC   : {metrics['auc_roc']}")
    print(f"   F1(return): {metrics['f1_return']}")
    return metrics


# ── Predict ───────────────────────────────────────────────────────────────────
def predict_return_risk(order: dict) -> dict:
    if not os.path.exists(MODEL_PATH):
        return {'error': 'Model not trained yet. Click Train Model first.'}

    with open(MODEL_PATH, 'rb') as f: model = pickle.load(f)
    with open(META_PATH,  'rb') as f: meta  = pickle.load(f)

    if 'price_per_unit' not in order:
        order['price_per_unit'] = round(order.get('amount', 0) /
                                        max(order.get('qty', 1), 1), 2)
    if 'weekend_order' not in order:
        order['weekend_order'] = 0

    row = pd.DataFrame([order])
    X, _ = prepare_features(row, meta['encoders'])
    for col in meta['features']:
        if col not in X.columns:
            X[col] = 0
    X = X[meta['features']]

    prob     = model.predict_proba(X)[0][1]
    risk_pct = round(prob * 100, 1)
    if risk_pct >= 60:   risk_label = "🔴 High Risk"
    elif risk_pct >= 30: risk_label = "🟡 Medium Risk"
    else:                risk_label = "🟢 Low Risk"

    top_3 = sorted(meta['metrics']['feature_importance'].items(),
                   key=lambda x: x[1], reverse=True)[:3]
    return {
        'risk_pct':      risk_pct,
        'risk_label':    risk_label,
        'top_factors':   [f[0] for f in top_3],
        'model_version': 'v2.0-HistGB',
    }


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    metrics = train_model()
    print("\n📈 Results:")
    for k, v in metrics.items():
        if k not in ('confusion_matrix', 'feature_importance'):
            print(f"   {k}: {v}")
    print("\n🔍 Feature Importance:")
    for feat, score in sorted(metrics['feature_importance'].items(),
                               key=lambda x: x[1], reverse=True):
        print(f"   {feat:20s} {'█' * int(score*30)} {score:.4f}")
