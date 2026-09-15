from datetime import datetime
from extensions import db


class Notification(db.Model):
    """Notification in-app (affichée en cloche + poussée en live via Socket.IO).
    Sert aussi de journal pour un futur relais SMS/push/email."""
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    type = db.Column(db.String(40), default="info")
    # order_status | promo | driver_assigned | review_reply | system | payment
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), default="")
    link = db.Column(db.String(255), nullable=True)   # url_for cible au clic

    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("notifications", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "link": self.link,
            "is_read": self.is_read,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else None,
        }

    def __repr__(self):
        return f"<Notification #{self.id} [{self.type}] user={self.user_id}>"
