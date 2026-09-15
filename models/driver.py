from datetime import datetime
from extensions import db


class Driver(db.Model):
    """Profil livreur — rattaché à un User (role='driver')."""
    __tablename__ = "drivers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)

    phone = db.Column(db.String(50), default="")
    vehicle_type = db.Column(db.String(30), default="moto")  # moto | velo | voiture | pied
    plate_number = db.Column(db.String(30), default="")
    photo = db.Column(db.String(200), nullable=True)

    is_active = db.Column(db.Boolean, default=True)       # compte activé par l'admin
    is_available = db.Column(db.Boolean, default=False)   # en ligne / dispo pour livrer

    # Position GPS en temps réel
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)

    # Réputation
    rating_avg = db.Column(db.Float, default=5.0)
    rating_count = db.Column(db.Integer, default=0)
    total_deliveries = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    user = db.relationship("User", backref=db.backref("driver_profile", uselist=False))
    orders = db.relationship("Order", back_populates="driver", foreign_keys="Order.driver_id")

    @property
    def status_label(self):
        if not self.is_active:
            return "Désactivé"
        return "En ligne" if self.is_available else "Hors ligne"

    def __repr__(self):
        return f"<Driver {self.user_id} [{self.status_label}]>"
