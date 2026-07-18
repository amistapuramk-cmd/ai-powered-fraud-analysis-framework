"""
ML anomaly detection model for the fraud framework.

Uses scikit-learn's IsolationForest - an unsupervised algorithm well suited
to fraud detection because it doesn't require labeled fraud examples. It
isolates observations by randomly partitioning the feature space; anomalies
(like fraud) tend to be isolated in fewer splits than normal points.

The model is trained on the numeric features of whatever transaction batch
is currently loaded, then produces an anomaly score for every row, which we
normalize to a 0-100 scale (higher = more anomalous).
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "isolation_forest.joblib")

FEATURE_COLUMNS = [
    "amount",
    "distance_from_home_km",
    "txn_hour",
    "velocity_last_hour",
    "card_present",
    "is_new_merchant_category",
]


def _to_feature_frame(transactions):
    df = pd.DataFrame(transactions)
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0
    return df[FEATURE_COLUMNS]


def train_model(transactions, contamination=0.06):
    """
    Trains a fresh IsolationForest on the given list of transaction dicts
    and persists it to disk. contamination = expected proportion of
    anomalies in the data (tune this to your real fraud base rate).
    """
    X = _to_feature_frame(transactions)
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42
    )
    model.fit(X)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


def score_transactions(transactions, model=None):
    """
    Returns a list of anomaly scores (0-100, higher = more anomalous)
    aligned with the input transaction list. Loads the persisted model
    if one isn't passed in.
    """
    if model is None:
        model = load_model()
    if model is None:
        # No trained model yet - return neutral scores
        return [0.0] * len(transactions)

    X = _to_feature_frame(transactions)
    # decision_function: higher = more "normal", lower/negative = more anomalous
    raw_scores = model.decision_function(X)

    # Normalize: invert so higher = more anomalous, then min-max scale to 0-100
    inverted = -raw_scores
    min_v, max_v = inverted.min(), inverted.max()
    if max_v - min_v < 1e-9:
        normalized = np.zeros_like(inverted)
    else:
        normalized = (inverted - min_v) / (max_v - min_v) * 100

    return [round(float(s), 2) for s in normalized]
