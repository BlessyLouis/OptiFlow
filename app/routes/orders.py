from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.order import Order
from app.models.order_history import OrderHistory
from app.services import inventory_service
from app.services.sla_prediction import predict_risk_score
from app.utils.constants import (
    ORDER_STATUSES, LENS_TYPES, STORE_LOCATIONS, COATINGS, LENS_INDEXES,
    SLA_BY_LENS_TYPE, ACTIVE_STATUSES,
)
from app.utils.logger import get_logger
import random
import string

bp = Blueprint("orders", __name__, url_prefix="/orders")
logger = get_logger(__name__)


def _generate_order_id() -> str:
    suffix = "".join(random.choices(string.digits, k=4))
    return f"ORD-{suffix}"


@bp.route("/")
def list_orders():
    status_filter = request.args.get("status", "")
    store_filter = request.args.get("store", "")
    lens_filter = request.args.get("lens_type", "")
    page = request.args.get("page", 1, type=int)

    query = Order.query

    if status_filter:
        query = query.filter(Order.current_status == status_filter)
    if store_filter:
        query = query.filter(Order.store_location == store_filter)
    if lens_filter:
        query = query.filter(Order.lens_type == lens_filter)

    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=25, error_out=False)

    return render_template(
        "orders.html",
        orders=orders,
        order_statuses=ORDER_STATUSES,
        lens_types=LENS_TYPES,
        store_locations=STORE_LOCATIONS,
        active_filters={"status": status_filter, "store": store_filter, "lens_type": lens_filter},
        now=datetime.utcnow(),
    )


@bp.route("/new", methods=["GET", "POST"])
def create_order():
    if request.method == "POST":
        lens_type = request.form["lens_type"]
        sla_hours = SLA_BY_LENS_TYPE.get(lens_type, 72)
        expected_delivery = datetime.utcnow() + timedelta(hours=sla_hours)

        order = Order(
            order_id=_generate_order_id(),
            customer_name=request.form["customer_name"],
            store_location=request.form["store_location"],
            prescription_power=request.form["prescription_power"],
            lens_type=lens_type,
            lens_index=request.form["lens_index"],
            coating=request.form["coating"],
            frame_name=request.form.get("frame_name", ""),
            current_status="Prescription Verified",
            sla_hours=sla_hours,
            expected_delivery=expected_delivery,
        )

        db.session.add(order)
        db.session.flush()

        inventory_service.check_and_allocate(order)
        order.risk_score = predict_risk_score(order)

        history = OrderHistory(
            order_id=order.id,
            status="Prescription Verified",
            remarks="Order created and prescription verified.",
        )
        db.session.add(history)
        db.session.commit()

        logger.info("New order created: %s for %s", order.order_id, order.customer_name)
        flash(f"Order {order.order_id} created successfully.", "success")
        return redirect(url_for("orders.order_detail", order_id=order.order_id))

    return render_template(
        "order_form.html",
        lens_types=LENS_TYPES,
        store_locations=STORE_LOCATIONS,
        coatings=COATINGS,
        lens_indexes=LENS_INDEXES,
    )


@bp.route("/<order_id>")
def order_detail(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    history = order.history.order_by(OrderHistory.timestamp.asc()).all()
    return render_template("order_detail.html", order=order, history=history, now=datetime.utcnow())


@bp.route("/<order_id>/advance", methods=["POST"])
def advance_status(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    new_status = request.form.get("new_status")
    remarks = request.form.get("remarks", "")

    if new_status not in ORDER_STATUSES:
        flash("Invalid status.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    if new_status == "QC Failed":
        order.qc_failure_count += 1
        order.delay_reason = "QC failure — rework initiated"

    order.current_status = new_status
    order.risk_score = predict_risk_score(order)

    db.session.add(
        OrderHistory(order_id=order.id, status=new_status, remarks=remarks or f"Status advanced to {new_status}.")
    )
    db.session.commit()

    logger.info("Order %s advanced to %s", order_id, new_status)
    flash(f"Status updated to '{new_status}'.", "success")
    return redirect(url_for("orders.order_detail", order_id=order_id))


@bp.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    results = (
        Order.query.filter(
            (Order.order_id.ilike(f"%{q}%")) | (Order.customer_name.ilike(f"%{q}%"))
        )
        .limit(10)
        .all()
    )
    return jsonify([o.to_dict() for o in results])
