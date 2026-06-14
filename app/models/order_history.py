from datetime import datetime
from app import db


class OrderHistory(db.Model):
    __tablename__ = "order_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<OrderHistory order={self.order_id} status={self.status}>"

    def to_dict(self):
        return {
            "status": self.status,
            "remarks": self.remarks,
            "timestamp": self.timestamp.isoformat(),
        }
