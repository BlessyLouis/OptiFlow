from datetime import datetime
from app import db
from app.utils.constants import RISK_LEVELS


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(120), nullable=False)
    store_location = db.Column(db.String(100), nullable=False)
    prescription_power = db.Column(db.String(20), nullable=False)  # e.g. "-2.50"
    lens_type = db.Column(db.String(50), nullable=False)
    lens_index = db.Column(db.String(10), nullable=False)
    coating = db.Column(db.String(50), nullable=False)
    frame_name = db.Column(db.String(100), nullable=True)
    current_status = db.Column(db.String(50), nullable=False, default="Prescription Verified")
    sla_hours = db.Column(db.Integer, nullable=False)
    risk_score = db.Column(db.Float, nullable=True, default=0.0)
    delay_reason = db.Column(db.String(200), nullable=True)
    expected_delivery = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    qc_failure_count = db.Column(db.Integer, default=0)
    inventory_available = db.Column(db.Boolean, default=True)

    history = db.relationship(
        "OrderHistory", backref="order", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Order {self.order_id} — {self.current_status}>"

    @property
    def is_active(self):
        return self.current_status not in ("Delivered", "Cancelled")

    @property
    def sla_remaining_hours(self):
        if not self.expected_delivery:
            return None
        delta = self.expected_delivery - datetime.utcnow()
        return round(delta.total_seconds() / 3600, 1)

    @property
    def risk_label(self):
        score = self.risk_score or 0
        if score <= RISK_LEVELS["LOW"][1]:
            return "LOW"
        elif score <= RISK_LEVELS["MEDIUM"][1]:
            return "MEDIUM"
        return "HIGH"

    @property
    def risk_badge_class(self):
        mapping = {"LOW": "badge-risk-low", "MEDIUM": "badge-risk-medium", "HIGH": "badge-risk-high"}
        return mapping.get(self.risk_label, "badge-risk-low")

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "customer_name": self.customer_name,
            "store_location": self.store_location,
            "lens_type": self.lens_type,
            "current_status": self.current_status,
            "risk_score": self.risk_score,
            "sla_remaining_hours": self.sla_remaining_hours,
            "delay_reason": self.delay_reason,
        }
