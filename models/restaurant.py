from datetime import datetime
from extensions import db


# Catégories disponibles
CATEGORIES = {
    "restaurant":  {"label": "Restaurant",          "icon": "🍽️",  "color": "#dc2626"},
    "supermarche": {"label": "Supermarché",         "icon": "🛒",  "color": "#2563eb"},
    "fruiterie":   {"label": "Fruiterie",           "icon": "🍎",  "color": "#16a34a"},
    "boulangerie": {"label": "Boulangerie & Pâtisserie", "icon": "🥐",  "color": "#d97706"},
}


class Restaurant(db.Model):
    __tablename__ = "restaurant"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False)
    description     = db.Column(db.Text, default="")
    address         = db.Column(db.String(250), default="")
    image           = db.Column(db.String(200), default="")
    commission_rate = db.Column(db.Float, default=10.0)
    is_active       = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Catégorie : restaurant | supermarche | fruiterie | boulangerie
    category = db.Column(db.String(50), default="restaurant", nullable=False)

    # Géolocalisation
    latitude           = db.Column(db.Float, nullable=True)
    longitude          = db.Column(db.Float, nullable=True)
    delivery_radius_km = db.Column(db.Float, default=5.0)

    # Vidéo de présentation du commerce
    video_file = db.Column(db.String(200), nullable=True)
    video_url  = db.Column(db.String(500), nullable=True)

    owner_id   = db.Column(db.Integer, db.ForeignKey("user.id"),     nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey("partners.id"), nullable=False)

    # Relations
    owner    = db.relationship("User",    back_populates="restaurants")
    partner  = db.relationship("Partner", back_populates="restaurants")
    products = db.relationship("Product", back_populates="restaurant", cascade="all, delete-orphan")
    orders   = db.relationship("Order",   back_populates="restaurant", cascade="all, delete-orphan")

    @property
    def category_info(self):
        return CATEGORIES.get(self.category, CATEGORIES["restaurant"])

    @property
    def category_label(self):
        return self.category_info["label"]

    @property
    def category_icon(self):
        return self.category_info["icon"]

    @property
    def category_color(self):
        return self.category_info["color"]

    def __repr__(self):
        return f"<Restaurant {self.name} [{self.category}]>"
