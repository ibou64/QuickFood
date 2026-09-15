from datetime import datetime
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="client")  # client | partner | admin | driver
    is_admin = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(50), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    restaurants = db.relationship(
        "Restaurant", back_populates="owner", cascade="all, delete-orphan"
    )
    orders = db.relationship(
        "Order", back_populates="user", cascade="all, delete-orphan"
    )
    partner = db.relationship(
        "Partner", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"
