from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from sqlalchemy import func
from app import db
from app.models.order import Order
from app.utils.constants import ACTIVE_STATUSES
from app.utils.logger import get_logger

bp = Blueprint("analytics", __name__, url_prefix="/analytics")
logger = get_logger(__name__)


@bp.route("/")
def index():
    return render_template("analytics.html")


@bp.route("/api/summary")
def api_summary():
    status_counts = dict(
        db.session.query(Order.current_status, func.count(Order.id))
        .group_by(Order.current_status)
        .all()
    )

    sla_on_time = Order.query.filter(
        Order.current_status == "Delivered", Order.risk_score < 71
    ).count()
    sla_breach = Order.query.filter(
        Order.current_status == "Delivered", Order.risk_score >= 71
    ).count()

    store_risk = (
        db.session.query(Order.store_location, func.avg(Order.risk_score))
        .group_by(Order.store_location)
        .order_by(func.avg(Order.risk_score).desc())
        .all()
    )

    qc_trend = _qc_trend_last_30_days()

    inv_by_type = (
        db.session.query(Order.lens_type, func.count(Order.id))
        .group_by(Order.lens_type)
        .all()
    )

    breach_trend = _breach_trend_last_7_days()

    return jsonify({
        "status_counts": status_counts,
        "sla": {"on_time": sla_on_time, "breach": sla_breach},
        "store_risk": [{"store": s, "avg_risk": round(r or 0, 1)} for s, r in store_risk],
        "qc_trend": qc_trend,
        "inventory_by_lens": [{"lens_type": lt, "orders": c} for lt, c in inv_by_type],
        "breach_trend": breach_trend,
    })


def _qc_trend_last_30_days():
    since = datetime.utcnow() - timedelta(days=30)
    rows = (
        db.session.query(func.date(Order.created_at), func.sum(Order.qc_failure_count))
        .filter(Order.created_at >= since)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )
    return [{"date": str(r[0]), "failures": int(r[1] or 0)} for r in rows]


def _breach_trend_last_7_days():
    result = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = Order.query.filter(
            Order.risk_score >= 71,
            Order.created_at >= day_start,
            Order.created_at <= day_end,
        ).count()
        result.append({"date": day.strftime("%b %d"), "count": count})
    return result
