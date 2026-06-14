from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.services import inventory_service
from app.services.inventory_forecast import get_forecast_recommendations
from app.utils.logger import get_logger

bp = Blueprint("inventory", __name__, url_prefix="/inventory")
logger = get_logger(__name__)


@bp.route("/")
def list_inventory():
    status_filter = request.args.get("status", "")
    lens_filter = request.args.get("lens_type", "")

    from app.models.inventory import Inventory
    query = Inventory.query

    if lens_filter:
        query = query.filter(Inventory.lens_type == lens_filter)

    items = query.order_by(Inventory.lens_type, Inventory.lens_power).all()

    if status_filter == "low_stock":
        items = [i for i in items if i.stock_status == "low_stock"]
    elif status_filter == "out_of_stock":
        items = [i for i in items if i.stock_status == "out_of_stock"]

    low_count = sum(1 for i in items if i.stock_status == "low_stock")
    out_count = sum(1 for i in items if i.stock_status == "out_of_stock")

    from app.utils.constants import LENS_TYPES
    return render_template(
        "inventory.html",
        items=items,
        low_count=low_count,
        out_count=out_count,
        lens_types=LENS_TYPES,
        active_filters={"status": status_filter, "lens_type": lens_filter},
    )


@bp.route("/forecast")
def forecast():
    recommendations = get_forecast_recommendations()
    return render_template("forecast.html", recommendations=recommendations)


@bp.route("/<int:inventory_id>/restock", methods=["POST"])
def restock(inventory_id):
    try:
        qty = int(request.form.get("quantity", 0))
    except ValueError:
        flash("Invalid quantity.", "danger")
        return redirect(url_for("inventory.list_inventory"))

    if qty <= 0:
        flash("Quantity must be greater than zero.", "danger")
        return redirect(url_for("inventory.list_inventory"))

    success = inventory_service.restock_item(inventory_id, qty)
    if success:
        flash(f"Restocked {qty} units successfully.", "success")
    else:
        flash("Inventory item not found.", "danger")

    return redirect(url_for("inventory.list_inventory"))


@bp.route("/api/status")
def api_status():
    """JSON endpoint for dashboard widgets."""
    from app.models.inventory import Inventory
    items = Inventory.query.all()
    return jsonify([i.to_dict() for i in items])
