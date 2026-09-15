from datetime import datetime
from extensions import db


class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    # Visiteur non connecté
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), nullable=False)
    phone      = db.Column(db.String(50),  default="")
    subject    = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    category   = db.Column(db.String(50),  default="general")
    # general | commande | paiement | livraison | technique | partenaire | autre
    status     = db.Column(db.String(20),  default="ouvert")
    # ouvert | en_cours | resolu | ferme
    priority   = db.Column(db.String(10),  default="normale")
    # basse | normale | haute | urgente
    response   = db.Column(db.Text,        nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
    order_id   = db.Column(db.Integer,     nullable=True)

    # Relation
    user = db.relationship("User", backref="support_tickets")

    @property
    def status_badge(self):
        badges = {
            "ouvert":   ("bg-warning text-dark", "Ouvert"),
            "en_cours": ("bg-info",              "En cours"),
            "resolu":   ("bg-success",           "Résolu"),
            "ferme":    ("bg-secondary",         "Fermé"),
        }
        return badges.get(self.status, ("bg-secondary", self.status))

    @property
    def category_label(self):
        labels = {
            "general":    "Général",
            "commande":   "Commande",
            "paiement":   "Paiement",
            "livraison":  "Livraison",
            "technique":  "Technique",
            "partenaire": "Partenaire",
            "autre":      "Autre",
        }
        return labels.get(self.category, self.category)

    def __repr__(self):
        return f"<Ticket #{self.id} [{self.status}]>"
