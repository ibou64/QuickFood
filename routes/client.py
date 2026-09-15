from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from models.order import Order
from models.review import Review
from utils.helpers import client_required

client_bp = Blueprint("client", __name__, url_prefix="/client")


@client_bp.route("/dashboard")
@login_required
@client_required
def dashboard():
    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("client_dashboard.html", user=current_user, orders=orders)


@client_bp.route("/orders")
@login_required
@client_required
def orders():
    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    reviewed_order_ids = {
        r.order_id for r in Review.query.filter_by(user_id=current_user.id).all() if r.order_id
    }
    return render_template("client_orders.html", orders=orders, reviewed_order_ids=reviewed_order_ids)


@client_bp.route("/orders/<int:order_id>/track")
@login_required
@client_required
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Non autorisé.", "danger")
        return redirect(url_for("client.orders"))
    return render_template("track_order.html", order=order)
