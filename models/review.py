from datetime import datetime
from extensions import db


class Review(db.Model):
    """Avis client sur un restaurant (et optionnellement sur une commande précise)."""
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurant.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)

    rating = db.Column(db.Integer, nullable=False)   # 1 à 5
    comment = db.Column(db.Text, default="")

    # Réponse du partenaire (optionnelle)
    reply = db.Column(db.Text, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
    restaurant = db.relationship("Restaurant", backref=db.backref("reviews", cascade="all, delete-orphan"))
    order = db.relationship("Order")

    __table_args__ = (
        db.UniqueConstraint("user_id", "order_id", name="uq_review_user_order"),
    )

    def __repr__(self):
        return f"<Review {self.rating}★ restaurant={self.restaurant_id}>"


class DriverReview(db.Model):
    """Avis client sur un livreur, laissé après livraison."""
    __tablename__ = "driver_reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)

    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
    driver = db.relationship("Driver", backref=db.backref("reviews", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<DriverReview {self.rating}★ driver={self.driver_id}>"
