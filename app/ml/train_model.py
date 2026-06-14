"""
Train a Random Forest classifier to predict SLA breach probability.

Run this script directly to train and save the model:
    python -m app.ml.train_model

The model is saved as app/ml/sla_model.pkl and loaded at runtime
by app/services/sla_prediction.py.
"""

import os
import sys
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Ensure imports work when run as a module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.constants import LENS_TYPES, STORE_LOCATIONS, ORDER_STATUSES

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "sla_model.pkl")

# Feature indices:
# [0] lens_type_enc, [1] inventory_unavailable, [2] status_enc, [3] qc_failures, [4] store_enc


def generate_training_data(n_samples: int = 3000):
    """Synthesise realistic training data for the SLA breach classifier."""
    rng = np.random.default_rng(42)

    lens_types = rng.integers(0, len(LENS_TYPES), n_samples)
    inventory_flag = rng.integers(0, 2, n_samples)  # 0=available, 1=unavailable
    statuses = rng.integers(0, len(ORDER_STATUSES), n_samples)
    qc_failures = rng.integers(0, 4, n_samples)
    stores = rng.integers(0, len(STORE_LOCATIONS), n_samples)

    X = np.column_stack([lens_types, inventory_flag, statuses, qc_failures, stores])

    # Label logic: mirrors the heuristic in sla_prediction.py
    base_risk = np.zeros(n_samples)
    base_risk += inventory_flag * 0.35
    base_risk += np.where(qc_failures >= 1, qc_failures * 0.20, 0)
    # Progressive=4, Photochromic=5 → higher risk
    base_risk += np.where(np.isin(lens_types, [4, 5]), 0.15, 0)
    # QC Failed=3, Reorder Generated=4
    base_risk += np.where(np.isin(statuses, [3, 4]), 0.20, 0)
    base_risk += rng.uniform(-0.1, 0.1, n_samples)  # noise

    y = (base_risk >= 0.5).astype(int)

    return X, y


def train():
    print("Generating synthetic training data...")
    X, y = generate_training_data(3000)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training Random Forest classifier...")
    clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    print("\nModel evaluation on test set:")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["On Time", "SLA Breach"]))

    bundle = {
        "model": clf,
        "encoders": {
            "lens_types": LENS_TYPES,
            "order_statuses": ORDER_STATUSES,
            "store_locations": STORE_LOCATIONS,
        },
    }
    joblib.dump(bundle, OUTPUT_PATH)
    print(f"\nModel saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    train()
