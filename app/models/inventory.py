from app import db


class Inventory(db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True)
    lens_power = db.Column(db.String(20), nullable=False)
    lens_type = db.Column(db.String(50), nullable=False)
    coating = db.Column(db.String(50), nullable=False)
    lens_index = db.Column(db.String(10), nullable=False)
    quantity_available = db.Column(db.Integer, nullable=False, default=0)
    reorder_threshold = db.Column(db.Integer, nullable=False, default=20)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("lens_power", "lens_type", "coating", "lens_index", name="uq_lens_sku"),
    )

    def __repr__(self):
        return f"<Inventory {self.lens_type} {self.lens_power} × {self.quantity_available}>"

    @property
    def stock_status(self):
        if self.quantity_available == 0:
            return "out_of_stock"
        elif self.quantity_available <= self.reorder_threshold:
            return "low_stock"
        return "in_stock"

    @property
    def stock_status_label(self):
        mapping = {
            "out_of_stock": "Out of Stock",
            "low_stock": "Low Stock",
            "in_stock": "In Stock",
        }
        return mapping.get(self.stock_status, "Unknown")

    def to_dict(self):
        return {
            "id": self.id,
            "lens_power": self.lens_power,
            "lens_type": self.lens_type,
            "coating": self.coating,
            "lens_index": self.lens_index,
            "quantity_available": self.quantity_available,
            "reorder_threshold": self.reorder_threshold,
            "stock_status": self.stock_status,
        }
