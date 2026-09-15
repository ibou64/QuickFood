"""Espace livreur : disponibilité, position GPS, livraisons en cours."""
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.driver import Driver
from models.order import Order
from services.driver_service import DriverService

driver_bp = Blueprint("driver", __name__, url_prefix="/driver")


def driver_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "driver":
            flash("Accès réservé aux livreurs.", "danger")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated


def _get_driver():
    return Driver.query.filter_by(user_id=current_user.id).first()


@driver_bp.route("/dashboard")
@login_required
@driver_required
def dashboard():
    driver = _get_driver()
    if not driver:
        flash("Profil livreur introuvable, contactez l'administrateur.", "danger")
        return redirect(url_for("main.home"))

    active_orders = (
        Order.query.filter_by(driver_id=driver.id)
        .filter(Order.status.in_(["Livreur assigné", "En livraison"]))
        .order_by(Order.driver_assigned_at.desc())
        .all()
    )
    history = (
        Order.query.filter_by(driver_id=driver.id, status="Livrée")
        .order_by(Order.delivered_at.desc())
        .limit(20).all()
    )
    return render_template("driver/dashboard.html", driver=driver,
                           active_orders=active_orders, history=history)


@driver_bp.route("/toggle-availability", methods=["POST"])
@login_required
@driver_required
def toggle_availability():
    driver = _get_driver()
    driver.is_available = not driver.is_available
    db.session.commit()
    return jsonify({"is_available": driver.is_available})


@driver_bp.route("/location", methods=["POST"])
@login_required
@driver_required
def update_location():
    driver = _get_driver()
    data = request.get_json(silent=True) or request.form
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "Coordonnées invalides"}), 400

    DriverService.update_location(driver, lat, lng)
    return jsonify({"ok": True})


@driver_bp.route("/order/<int:order_id>/picked-up", methods=["POST"])
@login_required
@driver_required
def mark_picked_up(order_id):
    order = Order.query.get_or_404(order_id)
    driver = _get_driver()
    if order.driver_id != driver.id:
        return jsonify({"error": "Non autorisé"}), 403
    order.status = "En livraison"
    order.picked_up_at = datetime.utcnow()
    db.session.commit()

    from services.notification_service import NotificationService
    NotificationService.order_status_changed(order)
    return jsonify({"ok": True})


@driver_bp.route("/order/<int:order_id>/delivered", methods=["POST"])
@login_required
@driver_required
def mark_delivered(order_id):
    order = Order.query.get_or_404(order_id)
    driver = _get_driver()
    if order.driver_id != driver.id:
        return jsonify({"error": "Non autorisé"}), 403
    DriverService.complete_delivery(order)
    return jsonify({"ok": True})
