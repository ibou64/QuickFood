from datetime import datetime
from extensions import db


class PromoCode(db.Model):
    """Code promo global ou restreint à un restaurant."""
    __tablename__ = "promo_codes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)  # ex: BIENVENUE10
    description = db.Column(db.String(200), default="")

    discount_type = db.Column(db.String(10), default="percent")  # percent | fixed
    discount_value = db.Column(db.Float, nullable=False)          # 10 (%) ou 1000 (FCFA)
    max_discount_amount = db.Column(db.Float, nullable=True)      # plafond si %

    min_order_amount = db.Column(db.Float, default=0.0)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurant.id"), nullable=True)  # null = valable partout

    max_uses = db.Column(db.Integer, nullable=True)       # null = illimité
    max_uses_per_user = db.Column(db.Integer, default=1)
    used_count = db.Column(db.Integer, default=0)

    valid_from = db.Column(db.DateTime, nullable=True)
    valid_until = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    restaurant = db.relationship("Restaurant")

    def is_valid_now(self) -> bool:
        if not self.is_active:
            return False
        now = datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def compute_discount(self, subtotal: float) -> float:
        if self.discount_type == "fixed":
            discount = self.discount_value
        else:
            discount = subtotal * (self.discount_value / 100.0)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        return round(min(discount, subtotal), 2)

    def __repr__(self):
        return f"<PromoCode {self.code}>"


class PromoRedemption(db.Model):
    """Historique d'utilisation d'un code promo par un utilisateur."""
    __tablename__ = "promo_redemptions"

    id = db.Column(db.Integer, primary_key=True)
    promo_id = db.Column(db.Integer, db.ForeignKey("promo_codes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    discount_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    promo = db.relationship("PromoCode", backref="redemptions")
    user = db.relationship("User")
