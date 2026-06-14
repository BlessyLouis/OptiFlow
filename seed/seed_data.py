"""
Seed script — generates realistic inventory and ~500 orders with full history.

Usage:
    flask shell
    >>> from seed.seed_data import seed
    >>> seed()

Or directly:
    python -c "from run import app; from seed.seed_data import seed; app.app_context().push(); seed()"
"""

import random
from datetime import datetime, timedelta
from app import db
from app.models.order import Order
from app.models.inventory import Inventory
from app.models.order_history import OrderHistory
from app.utils.constants import (
    LENS_TYPES, COATINGS, LENS_INDEXES, STORE_LOCATIONS,
    SLA_BY_LENS_TYPE, ORDER_STATUSES, DELAY_REASONS,
)

POWERS = [
    "-0.25", "-0.50", "-0.75", "-1.00", "-1.25", "-1.50",
    "-1.75", "-2.00", "-2.25", "-2.50", "-2.75", "-3.00",
    "+0.25", "+0.50", "+0.75", "+1.00", "+1.50", "+2.00",
    "-4.00", "-5.00", "-6.00",
]

FIRST_NAMES = [
    "Arjun", "Priya", "Rahul", "Sneha", "Amit", "Kavita",
    "Vikram", "Ananya", "Rohit", "Meena", "Suresh", "Divya",
    "Kartik", "Pooja", "Nikhil", "Smita", "Sanjay", "Ritu",
    "Deepak", "Nisha", "Akash", "Preeti", "Manish", "Sunita",
    "Aditya", "Rekha", "Gaurav", "Shweta", "Rajesh", "Anjali",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar",
    "Joshi", "Mehta", "Nair", "Reddy", "Iyer", "Pillai",
    "Chatterjee", "Banerjee", "Rao", "Mishra", "Agarwal", "Shah",
]

FRAMES = [
    "Ray-Ban RB3025", "Titan Eyeplus T301", "Vincent Chase VC6573",
    "Fastrack FT1278", "Lenskart Air A14457", "John Jacobs JJ E10884",
    "Carrera CA 1054", "Ted Baker TB 9154", "Oakley OX8046",
]

QC_REMARKS = [
    "Power mismatch — lens reordered",
    "Coating defect detected — rework initiated",
    "Axis deviation beyond tolerance — sent back to lab",
    "Scratch found during inspection — lens replaced",
]


def _random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _random_created_at():
    return datetime.utcnow() - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))


def seed_inventory():
    print("Seeding inventory...")
    Inventory.query.delete()
    items = []
    for lens_type in LENS_TYPES:
        for power in random.sample(POWERS, k=10):
            for coating in random.sample(COATINGS, k=3):
                index = random.choice(LENS_INDEXES)
                qty = random.choices(
                    [0, random.randint(1, 15), random.randint(16, 100)],
                    weights=[0.05, 0.25, 0.70],
                )[0]
                items.append(Inventory(
                    lens_power=power,
                    lens_type=lens_type,
                    coating=coating,
                    lens_index=index,
                    quantity_available=qty,
                    reorder_threshold=20,
                ))
    db.session.bulk_save_objects(items)
    db.session.commit()
    print(f"  Seeded {len(items)} inventory SKUs")


def seed_orders():
    print("Seeding orders...")
    Order.query.delete()
    OrderHistory.query.delete()

    # Pre-load inventory to use for cross-referencing
    inv_items = Inventory.query.all()
    inv_lookup = {(i.lens_power, i.lens_type, i.coating, i.lens_index): i for i in inv_items}

    orders = []
    histories = []
    used_ids = set()

    for n in range(500):
        while True:
            oid = f"ORD-{random.randint(1000, 9999)}"
            if oid not in used_ids:
                used_ids.add(oid)
                break

        lens_type = random.choice(LENS_TYPES)
        power = random.choice(POWERS)
        coating = random.choice(COATINGS)
        index = random.choice(LENS_INDEXES)
        store = random.choice(STORE_LOCATIONS)
        sla_hours = SLA_BY_LENS_TYPE[lens_type]
        created = _random_created_at()
        expected = created + timedelta(hours=sla_hours)

        inv_available = (power, lens_type, coating, index) in inv_lookup and inv_lookup[(power, lens_type, coating, index)].quantity_available > 0

        # Determine end status with realistic distribution
        qc_failures = random.choices([0, 1, 2], weights=[0.65, 0.25, 0.10])[0]
        if qc_failures > 0:
            status = random.choices(
                ["QC Failed", "Reorder Generated", "Lens Processing", "Packing", "Shipped", "Delivered"],
                weights=[0.1, 0.15, 0.15, 0.2, 0.2, 0.2],
            )[0]
        else:
            status = random.choices(
                ["Prescription Verified", "Lens Processing", "QC", "Packing", "Shipped", "Delivered"],
                weights=[0.08, 0.12, 0.12, 0.12, 0.18, 0.38],
            )[0]

        delay_reason = None
        if not inv_available or qc_failures > 0:
            delay_reason = random.choice([r for r in DELAY_REASONS if r])

        # Heuristic risk score
        risk = 15.0
        if not inv_available:
            risk += 35
        risk += qc_failures * 20
        if lens_type in ("Progressive", "Photochromic"):
            risk += 15
        if status in ("QC Failed", "Reorder Generated"):
            risk += 20
        risk += random.uniform(-5, 10)
        risk = max(0, min(round(risk, 1), 100))

        order = Order(
            order_id=oid,
            customer_name=_random_name(),
            store_location=store,
            prescription_power=power,
            lens_type=lens_type,
            lens_index=index,
            coating=coating,
            frame_name=random.choice(FRAMES),
            current_status=status,
            sla_hours=sla_hours,
            risk_score=risk,
            delay_reason=delay_reason,
            expected_delivery=expected,
            created_at=created,
            qc_failure_count=qc_failures,
            inventory_available=inv_available,
        )
        orders.append(order)

    db.session.bulk_save_objects(orders)
    db.session.flush()

    # Build order histories
    saved_orders = Order.query.all()
    status_flow = [
        "Prescription Verified", "Lens Processing", "QC",
        "Packing", "Shipped", "Delivered",
    ]

    for order in saved_orders:
        current_idx = status_flow.index(order.current_status) if order.current_status in status_flow else 1
        ts = order.created_at

        for step in status_flow[: current_idx + 1]:
            remark = f"Status updated to {step}."
            if step == "QC" and order.qc_failure_count > 0:
                histories.append(OrderHistory(order_id=order.id, status="QC Failed", remarks=random.choice(QC_REMARKS), timestamp=ts))
                ts += timedelta(hours=random.randint(2, 8))
                if order.qc_failure_count >= 2:
                    histories.append(OrderHistory(order_id=order.id, status="Reorder Generated", remarks="Second QC failure — reorder placed.", timestamp=ts))
                    ts += timedelta(hours=random.randint(4, 12))
            histories.append(OrderHistory(order_id=order.id, status=step, remarks=remark, timestamp=ts))
            ts += timedelta(hours=random.randint(1, 12))

    db.session.bulk_save_objects(histories)
    db.session.commit()
    print(f"  Seeded 500 orders and {len(histories)} history events")


def seed():
    seed_inventory()
    seed_orders()
    print("Seed complete.")
