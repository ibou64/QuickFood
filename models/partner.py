from extensions import db


class Partner(db.Model):
    __tablename__ = "partners"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), default="")
    n_rcm = db.Column(db.String(100), default="")
    address = db.Column(db.String(250), default="")
    is_active = db.Column(db.Boolean, default=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Relations
    user = db.relationship("User", back_populates="partner")
    restaurants = db.relationship(
        "Restaurant", back_populates="partner", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Partner {self.name}>"
