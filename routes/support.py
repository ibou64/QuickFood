"""
Blueprint support — Module support clients & partenaires QuickFood
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime

from extensions import db
from models.support import SupportTicket
from utils.security import sanitize_string, validate_email

support_bp = Blueprint("support", __name__, url_prefix="/support")

CATEGORIES = [
    ("general",    "💬 Général"),
    ("commande",   "📦 Commande"),
    ("paiement",   "💳 Paiement"),
    ("livraison",  "🛵 Livraison"),
    ("technique",  "⚙️ Problème technique"),
    ("partenaire", "🤝 Espace Partenaire"),
    ("autre",      "📝 Autre"),
]


@support_bp.route("/", methods=["GET", "POST"])
def index():
    """Page principale du support — formulaire de contact."""
    if request.method == "POST":
        # Récupérer et nettoyer les données
        name     = sanitize_string(request.form.get("name", "").strip(), 100)
        email    = request.form.get("email", "").strip().lower()
        phone    = sanitize_string(request.form.get("phone", "").strip(), 20)
        subject  = sanitize_string(request.form.get("subject", "").strip(), 200)
        message  = sanitize_string(request.form.get("message", "").strip(), 2000)
        category = request.form.get("category", "general")
        order_id = request.form.get("order_id", "").strip()

        # Validations
        if not name or not email or not subject or not message:
            flash("Veuillez remplir tous les champs obligatoires.", "danger")
            return redirect(url_for("support.index"))
        if not validate_email(email):
            flash("Adresse email invalide.", "danger")
            return redirect(url_for("support.index"))
        if len(message) < 10:
            flash("Message trop court (minimum 10 caractères).", "danger")
            return redirect(url_for("support.index"))

        # Créer le ticket
        ticket = SupportTicket(
            user_id   = current_user.id if current_user.is_authenticated else None,
            name      = name,
            email     = email,
            phone     = phone,
            subject   = subject,
            message   = message,
            category  = category if category in dict(CATEGORIES) else "general",
            order_id  = int(order_id) if order_id.isdigit() else None,
            priority  = "haute" if category in ("paiement", "livraison") else "normale",
        )
        db.session.add(ticket)
        db.session.commit()

        flash(f"Ticket #{ticket.id} créé avec succès ! Nous vous répondrons sous 24h à {email}.", "success")
        return redirect(url_for("support.ticket_detail", ticket_id=ticket.id))

    # Pré-remplir si connecté
    prefill = {}
    if current_user.is_authenticated:
        prefill = {"name": current_user.name, "email": current_user.email}

    return render_template("support/index.html", categories=CATEGORIES, prefill=prefill)


@support_bp.route("/ticket/<int:ticket_id>")
def ticket_detail(ticket_id):
    """Confirmation et détail d'un ticket."""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    # Sécurité : seul le créateur ou un admin peut voir
    if current_user.is_authenticated:
        if not current_user.is_admin and ticket.user_id != current_user.id:
            flash("Accès refusé.", "danger")
            return redirect(url_for("support.index"))
    return render_template("support/ticket_detail.html", ticket=ticket)


@support_bp.route("/mes-tickets")
@login_required
def my_tickets():
    """Liste des tickets de l'utilisateur connecté."""
    tickets = SupportTicket.query.filter_by(
        user_id=current_user.id
    ).order_by(SupportTicket.created_at.desc()).all()
    return render_template("support/my_tickets.html", tickets=tickets)


# ── Routes Admin ──────────────────────────────────────────

@support_bp.route("/admin/tickets")
@login_required
def admin_tickets():
    """Admin — liste de tous les tickets."""
    if not current_user.is_admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for("main.home"))

    status_filter = request.args.get("status", "")
    cat_filter    = request.args.get("category", "")
    q             = SupportTicket.query

    if status_filter:
        q = q.filter_by(status=status_filter)
    if cat_filter:
        q = q.filter_by(category=cat_filter)

    tickets = q.order_by(SupportTicket.created_at.desc()).all()
    stats = {
        "total":    SupportTicket.query.count(),
        "ouverts":  SupportTicket.query.filter_by(status="ouvert").count(),
        "en_cours": SupportTicket.query.filter_by(status="en_cours").count(),
        "resolus":  SupportTicket.query.filter_by(status="resolu").count(),
    }
    return render_template("support/admin_tickets.html",
                           tickets=tickets, stats=stats,
                           categories=CATEGORIES,
                           status_filter=status_filter,
                           cat_filter=cat_filter)


@support_bp.route("/admin/ticket/<int:ticket_id>/respond", methods=["POST"])
@login_required
def admin_respond(ticket_id):
    """Admin — répondre à un ticket et changer son statut."""
    if not current_user.is_admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for("main.home"))

    ticket = SupportTicket.query.get_or_404(ticket_id)
    response   = sanitize_string(request.form.get("response", "").strip(), 3000)
    new_status = request.form.get("status", ticket.status)

    if response:
        ticket.response   = response
    if new_status in ("ouvert", "en_cours", "resolu", "ferme"):
        ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    db.session.commit()

    flash(f"Ticket #{ticket.id} mis à jour.", "success")
    return redirect(url_for("support.admin_tickets"))
