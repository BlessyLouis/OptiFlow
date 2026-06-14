from typing import Optional
from app import db
from app.models.inventory import Inventory
from app.models.order import Order
from app.utils.logger import get_logger

logger = get_logger(__name__)


def find_inventory_item(lens_power: str, lens_type: str, coating: str, lens_index: str) -> Optional[Inventory]:
    return Inventory.query.filter_by(
        lens_power=lens_power,
        lens_type=lens_type,
        coating=coating,
        lens_index=lens_index,
    ).first()


def check_and_allocate(order: Order) -> bool:
    """
    Attempt to allocate inventory for an order.
    Returns True if stock was available and deducted, False otherwise.
    """
    item = find_inventory_item(
        order.prescription_power,
        order.lens_type,
        order.coating,
        order.lens_index,
    )

    if not item or item.quantity_available <= 0:
        logger.warning(
            "Inventory unavailable for order %s — %s %s %s",
            order.order_id, order.lens_type, order.prescription_power, order.coating,
        )
        order.inventory_available = False
        return False

    item.quantity_available -= 1
    order.inventory_available = True
    db.session.flush()
    logger.info("Allocated 1 unit of %s %s for order %s", order.lens_type, order.prescription_power, order.order_id)
    return True


def get_low_stock_items():
    return (
        Inventory.query.filter(
            Inventory.quantity_available <= Inventory.reorder_threshold,
            Inventory.quantity_available > 0,
        )
        .order_by(Inventory.quantity_available.asc())
        .all()
    )


def get_out_of_stock_items():
    return Inventory.query.filter(Inventory.quantity_available == 0).all()


def get_all_inventory():
    return Inventory.query.order_by(Inventory.lens_type, Inventory.lens_power).all()


def restock_item(inventory_id: int, quantity: int) -> bool:
    item = Inventory.query.get(inventory_id)
    if not item:
        return False
    item.quantity_available += quantity
    db.session.commit()
    logger.info("Restocked inventory id=%d by %d units", inventory_id, quantity)
    return True
