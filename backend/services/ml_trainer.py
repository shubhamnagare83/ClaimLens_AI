"""
ClaimLens AI — ML Training Pipeline on Kaggle Vehicle Insurance Dataset
Dataset: imtkaggleteam/vehicle-insurance-data (508,499 records)
"""
import os
import json
import joblib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix
import lightgbm as lgb

DATA_PATH = Path(r"C:\Users\lenovo\.cache\kagglehub\datasets\imtkaggleteam\vehicle-insurance-data\versions\1\motor_data14-2018.csv")
MODEL_DIR = Path(__file__).resolve().parent.parent / "ml"
MODEL_PATH = MODEL_DIR / "model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
BENCHMARKS_PATH = MODEL_DIR / "benchmarks.json"


def train_and_evaluate():
    print(f"Loading vehicle insurance dataset from: {DATA_PATH}")
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Read dataset sample for high-speed & high-quality training
    df = pd.read_csv(DATA_PATH, nrows=150000)
    print(f"Loaded {len(df):,} records for model training and validation.")

    # Target: 1 if claim paid, 0 otherwise
    df['has_claim'] = df['CLAIM_PAID'].notna().astype(int)

    # Compute benchmarks from actual claim payouts
    paid_claims = df[df['CLAIM_PAID'].notna() & (df['CLAIM_PAID'] > 0)]
    benchmarks = {
        'avg_payout_overall': float(paid_claims['CLAIM_PAID'].median()),
        'p75_payout_overall': float(paid_claims['CLAIM_PAID'].quantile(0.75)),
        'payout_by_vehicle_type': {},
        'payout_by_usage': {},
        'claim_rate_by_vehicle_type': {}
    }

    for vtype, grp in df.groupby('TYPE_VEHICLE'):
        if len(grp) > 50:
            v_paid = grp[grp['CLAIM_PAID'].notna() & (grp['CLAIM_PAID'] > 0)]
            med_pay = float(v_paid['CLAIM_PAID'].median()) if len(v_paid) > 0 else benchmarks['avg_payout_overall']
            benchmarks['payout_by_vehicle_type'][str(vtype)] = round(med_pay, 2)
            benchmarks['claim_rate_by_vehicle_type'][str(vtype)] = round(float(grp['has_claim'].mean()) * 100, 2)

    for usage, grp in df.groupby('USAGE'):
        if len(grp) > 50:
            u_paid = grp[grp['CLAIM_PAID'].notna() & (grp['CLAIM_PAID'] > 0)]
            med_pay = float(u_paid['CLAIM_PAID'].median()) if len(u_paid) > 0 else benchmarks['avg_payout_overall']
            benchmarks['payout_by_usage'][str(usage)] = round(med_pay, 2)

    # Feature Engineering
    df['VEHICLE_AGE'] = (2026 - df['PROD_YEAR']).clip(0, 40)
    df['PREMIUM_RATIO'] = (df['PREMIUM'] / (df['INSURED_VALUE'] + 1.0)).clip(0, 1.0)
    df['IDV_LOG'] = np.log1p(df['INSURED_VALUE'].clip(lower=0))
    df['CCM_TON'] = df['CCM_TON'].fillna(df['CCM_TON'].median())
    df['SEATS_NUM'] = df['SEATS_NUM'].fillna(5)
    df['CARRYING_CAPACITY'] = df['CARRYING_CAPACITY'].fillna(0)

    numeric_features = [
        'INSURED_VALUE', 'PREMIUM', 'VEHICLE_AGE',
        'SEATS_NUM', 'CARRYING_CAPACITY', 'CCM_TON',
        'PREMIUM_RATIO', 'IDV_LOG'
    ]
    categorical_features = ['TYPE_VEHICLE', 'USAGE']

    for col in categorical_features:
        df[col] = df[col].astype(str).astype('category')

    features = numeric_features + categorical_features
    X = df[features]
    y = df['has_claim']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Training LightGBM Classifier (Best Model for Tabular Claims)...")
    clf = lgb.LGBMClassifier(
        n_estimators=160,
        learning_rate=0.04,
        max_depth=6,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=2.5,
        random_state=42,
        verbosity=-1
    )

    clf.fit(X_train, y_train)

    # Evaluate
    preds = clf.predict(X_test)
    probs = clf.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, preds))
    auc = float(roc_auc_score(y_test, probs))
    prec = float(precision_score(y_test, preds, zero_division=0))
    rec = float(recall_score(y_test, preds, zero_division=0))
    f1 = float(f1_score(y_test, preds, zero_division=0))
    cm = confusion_matrix(y_test, preds).tolist()

    # Feature importances
    importances = clf.feature_importances_
    feat_imp = [
        {"feature": f, "importance": int(imp), "pct": round(float(imp) / float(importances.sum()) * 100, 1)}
        for f, imp in sorted(zip(features, importances), key=lambda x: x[1], reverse=True)
    ]

    metrics = {
        "model_name": "LightGBM Gradient Boosted Decision Trees",
        "dataset": "Kaggle imtkaggleteam/vehicle-insurance-data",
        "total_records": 508499,
        "sample_trained": len(df),
        "test_records": len(y_test),
        "accuracy": round(acc * 100, 2),
        "roc_auc": round(auc, 4),
        "precision": round(prec * 100, 2),
        "recall": round(rec * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "confusion_matrix": {
            "true_negatives": cm[0][0],
            "false_positives": cm[0][1],
            "false_negatives": cm[1][0],
            "true_positives": cm[1][1],
        },
        "feature_importances": feat_imp,
        "features_used": features,
        "categories": {
            "type_vehicle": [str(c) for c in df['TYPE_VEHICLE'].cat.categories],
            "usage": [str(c) for c in df['USAGE'].cat.categories]
        }
    }

    print(f"\nModel Performance Metrics:")
    print(f"Accuracy: {metrics['accuracy']}%")
    print(f"ROC-AUC: {metrics['roc_auc']}")
    print(f"Precision: {metrics['precision']}%")
    print(f"Recall: {metrics['recall']}%")
    print(f"F1-Score: {metrics['f1_score']}%")

    # Save artifacts
    joblib.dump(clf, MODEL_PATH)
    with open(METRICS_PATH, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    with open(BENCHMARKS_PATH, 'w', encoding='utf-8') as f:
        json.dump(benchmarks, f, indent=2)

    print(f"Saved model to: {MODEL_PATH}")
    print(f"Saved metrics to: {METRICS_PATH}")
    print(f"Saved benchmarks to: {BENCHMARKS_PATH}")
    return metrics


if __name__ == "__main__":
    train_and_evaluate()
