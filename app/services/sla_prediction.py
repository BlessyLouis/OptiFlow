import os
import joblib
import numpy as np
from app.utils.logger import get_logger
from app.utils.constants import LENS_TYPES, STORE_LOCATIONS, ORDER_STATUSES

logger = get_logger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "sla_model.pkl")

_model = None
_encoders = None


def _load_model():
    global _model, _encoders
    if _model is None:
        try:
            bundle = joblib.load(MODEL_PATH)
            _model = bundle["model"]
            _encoders = bundle["encoders"]
            logger.info("SLA prediction model loaded successfully")
        except FileNotFoundError:
            logger.warning("SLA model not found at %s — returning default scores", MODEL_PATH)
    return _model, _encoders


def _encode_feature(value: str, categories: list) -> int:
    """Ordinal encode a string feature, returning index or 0 if not found."""
    try:
        return categories.index(value)
    except ValueError:
        return 0


def predict_risk_score(order) -> float:
    """
    Predict SLA breach probability (0–100) for an order.
    Falls back to a heuristic score if model is unavailable.
    """
    model, encoders = _load_model()

    lens_type_enc = _encode_feature(order.lens_type, LENS_TYPES)
    status_enc = _encode_feature(order.current_status, ORDER_STATUSES)
    store_enc = _encode_feature(order.store_location, STORE_LOCATIONS)
    inventory_flag = 0 if order.inventory_available else 1
    qc_failures = order.qc_failure_count or 0

    features = np.array([[lens_type_enc, inventory_flag, status_enc, qc_failures, store_enc]])

    if model is not None:
        try:
            proba = model.predict_proba(features)[0][1]
            return round(proba * 100, 1)
        except Exception as e:
            logger.error("Model prediction failed: %s", e)

    # Heuristic fallback when model is absent
    score = 20.0
    if not order.inventory_available:
        score += 35
    if qc_failures >= 1:
        score += 20 * qc_failures
    if order.lens_type in ("Progressive", "Photochromic"):
        score += 15
    if order.current_status in ("QC Failed", "Reorder Generated"):
        score += 20

    return min(round(score, 1), 100.0)
