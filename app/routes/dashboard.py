from datetime import datetime
from flask import Blueprint, render_template
from sqlalchemy import func
from app import db
from app.models.order import Order
from app.models.inventory import Inventory
from app.utils.constants import ACTIVE_STATUSES
from app.utils.logger import get_logger

bp = Blueprint("dashboard", __name__)
logger = get_logger(__name__)


@bp.route("/")
def index():
    # KPI aggregations
    active_count = Order.query.filter(Order.current_status.in_(ACTIVE_STATUSES)).count()
    delivered_count = Order.query.filter(Order.current_status == "Delivered").count()
    at_risk_count = Order.query.filter(Order.risk_score >= 71).count()
    sla_breach_count = Order.query.filter(
        Order.expected_delivery < datetime.utcnow(),
        Order.current_status.in_(ACTIVE_STATUSES),
    ).count()

    # Recent high-risk orders for the dashboard table
    high_risk_orders = (
        Order.query.filter(Order.risk_score >= 71)
        .order_by(Order.risk_score.desc())
        .limit(10)
        .all()
    )

    # Recent orders feed
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(15).all()

    # Low stock alerts
    low_stock_items = (
        Inventory.query.filter(
            Inventory.quantity_available <= Inventory.reorder_threshold
        )
        .order_by(Inventory.quantity_available.asc())
        .limit(5)
        .all()
    )

    # Status distribution for mini chart data
    status_data = (
        db.session.query(Order.current_status, func.count(Order.id))
        .group_by(Order.current_status)
        .all()
    )
    status_chart = {row[0]: row[1] for row in status_data}

    return render_template(
        "dashboard.html",
        active_count=active_count,
        delivered_count=delivered_count,
        at_risk_count=at_risk_count,
        sla_breach_count=sla_breach_count,
        high_risk_orders=high_risk_orders,
        recent_orders=recent_orders,
        low_stock_items=low_stock_items,
        status_chart=status_chart,
        now=datetime.utcnow(),
    )
@bp.route("/ml/metrics")
def ml_metrics():
    import joblib
    import os
    from app.ml.train_model import generate_training_data
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import train_test_split

    model_path = os.path.join(os.path.dirname(__file__), "../ml/sla_model.pkl")
    bundle = joblib.load(model_path)
    model = bundle["model"]

    X, y = generate_training_data(3000)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred,
                target_names=["On Time", "SLA Breach"], output_dict=True)
    cm = confusion_matrix(y_test, y_pred).tolist()

    feature_names = ["Lens Type", "Inventory Flag", "Order Status", "QC Failures", "Store Location"]
    importances = list(zip(feature_names, [round(float(i), 4) for i in model.feature_importances_]))
    importances.sort(key=lambda x: x[1], reverse=True)

    return render_template("ml_metrics.html",
        report=report, cm=cm, importances=importances,
        n_estimators=model.n_estimators,
        max_depth=model.max_depth,
    )
