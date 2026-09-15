"""
Blueprint paiement — intégration PayTech.
"""
from flask import Blueprint, redirect, request, jsonify, url_for, flash, current_app
from flask_login import login_required, current_user

from extensions import db
from models.order import Order
from services.payment_service import PayTechService
from services.split_service import SplitService

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")


@payment_bp.route("/pay/<int:order_id>")
@login_required
def pay(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("main.home"))

    if order.payment_status == "success":
        flash("Cette commande est déjà payée.", "info")
        return redirect(url_for("client.orders"))

    # Vérifier que les clés PayTech sont configurées
    api_key    = current_app.config.get("PAYTECH_API_KEY", "")
    api_secret = current_app.config.get("PAYTECH_SECRET", "")

    if not api_key or not api_secret:
        flash(
            "⚠️ Paiement en ligne non configuré. "
            "Ajoutez vos clés PayTech dans le fichier .env — "
            "votre commande est confirmée avec paiement à la livraison.",
            "warning"
        )
        order.payment_status = "cash"
        order.status = "En attente"
        db.session.commit()
        return redirect(url_for("client.orders"))

    result = PayTechService.create_payment(
        order,
        success_url=url_for("payment.success", _external=True),
        cancel_url=url_for("payment.cancel", _external=True),
        ipn_url=url_for("payment.ipn", _external=True),
    )

    if result["success"]:
        order.ref_command    = result["ref"]
        order.payment_status = "pending"
        db.session.commit()
        return redirect(result["url"])

    # Erreur API PayTech → fallback paiement à la livraison
    flash(
        f"Paiement en ligne indisponible ({result.get('error', 'erreur inconnue')}). "
        "Commande confirmée — paiement à la livraison.",
        "warning"
    )
    order.payment_status = "cash"
    order.status = "En attente"
    db.session.commit()
    return redirect(url_for("client.orders"))


@payment_bp.route("/ipn", methods=["POST"])
def ipn():
    """
    IPN (Instant Payment Notification) PayTech.
    PayTech poste ref_command + type_event une fois le paiement validé.
    """
    data = request.form.to_dict() or request.get_json(silent=True) or {}

    ref_command = data.get("ref_command")
    type_event  = data.get("type_event", "")   # "sale_complete" quand confirmé

    if not ref_command:
        return jsonify({"status": "error", "msg": "ref_command manquant"}), 400

    order = Order.query.filter_by(ref_command=ref_command).first()

    if not order:
        return jsonify({"status": "error", "msg": "commande introuvable"}), 404

    if type_event == "sale_complete" and order.payment_status != "success":
        order.payment_status = "success"
        order.status = "En préparation"
        db.session.commit()

        # ── SPLIT AUTOMATIQUE ──────────────────────────────────────────────
        # Dès que le paiement est confirmé, on calcule et enregistre
        # la répartition : commission QuickFood + montant restaurant.
        SplitService.execute(order)
        # ──────────────────────────────────────────────────────────────────

    return jsonify({"status": "ok"}), 200


@payment_bp.route("/success")
def success():
    flash("Paiement réussi ! Votre commande est en cours de préparation. 🎉", "success")
    return redirect(url_for("client.orders"))


@payment_bp.route("/cancel")
def cancel():
    flash("Paiement annulé. Votre commande est conservée — vous pouvez réessayer.", "warning")
    return redirect(url_for("client.orders"))
