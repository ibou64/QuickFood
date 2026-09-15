from datetime import datetime
from extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurant.id"), nullable=False)

    # Montants
    subtotal      = db.Column(db.Float, default=0.0)
    delivery_fee  = db.Column(db.Float, default=1000.0)
    total_amount  = db.Column(db.Float, default=0.0)
    ref_command = db.Column(db.String(255), nullable=True)

    status     = db.Column(db.String(50), default="En attente")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Livraison
    delivery_address  = db.Column(db.String(255), default="")
    delivery_phone    = db.Column(db.String(50),  default="")
    delivery_name     = db.Column(db.String(100), default="")
    delivery_latitude  = db.Column(db.Float, nullable=True)
    delivery_longitude = db.Column(db.Float, nullable=True)
    delivery_distance  = db.Column(db.Float, nullable=True)   # en km

    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
    driver_assigned_at = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)

    # Paiement PayTech
    payment_status = db.Column(db.String(50), default="pending")
    # pending | success | failed | cancelled | cash

    # ── PROMO / RÉDUCTION ────────────────────────────────────────────────────
    promo_code_id = db.Column(db.Integer, db.ForeignKey("promo_codes.id"), nullable=True)
    discount_amount = db.Column(db.Float, default=0.0)
    promo = db.relationship("PromoCode")

    # ── SPLIT PAYMENT ──────────────────────────────────────────────────────────
    # Calculé automatiquement à la confirmation IPN (type_event=sale_complete)
    commission_rate   = db.Column(db.Float,      nullable=True)     # ex: 10.0 (%)
    commission_amount = db.Column(db.Float,      nullable=True)     # part QuickFood (XOF)
    restaurant_amount = db.Column(db.Float,      nullable=True)     # part restaurant (XOF)
    split_status      = db.Column(db.String(30), default="pending") # pending|done|error
    split_done_at     = db.Column(db.DateTime,   nullable=True)
    # ──────────────────────────────────────────────────────────────────────────

    # Relations
    user       = db.relationship("User",       back_populates="orders")
    restaurant = db.relationship("Restaurant", back_populates="orders")
    items      = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    driver     = db.relationship("Driver", back_populates="orders", foreign_keys=[driver_id])

    # Statuts possibles côté livraison, dans l'ordre du cycle de vie :
    # "En attente" -> "Confirmée" -> "En préparation" -> "Prête" ->
    # "Livreur assigné" -> "En livraison" -> "Livrée"  (ou "Annulée")
    DELIVERY_STATUSES = [
        "En attente", "Confirmée", "En préparation", "Prête",
        "Livreur assigné", "En livraison", "Livrée", "Annulée",
    ]

    @property
    def total(self):
        """Alias pour compatibilité."""
        return self.total_amount

    def __repr__(self):
        return f"<Order #{self.id} - {self.status}>"
