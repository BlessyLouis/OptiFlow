from datetime import datetime, timedelta
from collections import defaultdict
from app.models.inventory import Inventory
from app.models.order import Order
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Look-back window for consumption rate calculation
ANALYSIS_WINDOW_DAYS = 30


def _calculate_daily_consumption(lens_type: str, lens_power: str, coating: str) -> float:
    """Compute average units consumed per day for a given SKU over the analysis window."""
    since = datetime.utcnow() - timedelta(days=ANALYSIS_WINDOW_DAYS)
    count = Order.query.filter(
        Order.lens_type == lens_type,
        Order.prescription_power == lens_power,
        Order.coating == coating,
        Order.created_at >= since,
    ).count()
    return round(count / ANALYSIS_WINDOW_DAYS, 2)


def get_forecast_recommendations():
    """
    For each inventory SKU, compute days until stockout and suggest reorder quantity.
    Returns a list of recommendation dicts sorted by urgency.
    """
    items = Inventory.query.filter(Inventory.quantity_available > 0).all()
    recommendations = []

    for item in items:
        daily_rate = _calculate_daily_consumption(item.lens_type, item.lens_power, item.coating)

        if daily_rate <= 0:
            continue  # No recent demand, skip

        days_until_stockout = round(item.quantity_available / daily_rate, 1)
        # Suggested reorder = 14-day buffer based on current consumption rate
        suggested_qty = max(10, round(daily_rate * 14))

        if days_until_stockout <= 14:  # Only surface items at risk within 2 weeks
            recommendations.append({
                "inventory_id": item.id,
                "lens_power": item.lens_power,
                "lens_type": item.lens_type,
                "coating": item.coating,
                "lens_index": item.lens_index,
                "quantity_available": item.quantity_available,
                "daily_rate": daily_rate,
                "days_until_stockout": days_until_stockout,
                "suggested_reorder_qty": suggested_qty,
                "urgency": "critical" if days_until_stockout <= 5 else "warning",
            })

    recommendations.sort(key=lambda x: x["days_until_stockout"])
    logger.info("Generated %d inventory forecast recommendations", len(recommendations))
    return recommendations
