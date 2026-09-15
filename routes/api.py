from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from models.restaurant import Restaurant
from models.product import Product
from models.order import Order

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/restaurants")
def get_restaurants():
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    return jsonify([
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "image": r.image,
            "address": r.address,
        }
        for r in restaurants
    ])


@api_bp.route("/restaurants/<int:restaurant_id>/products")
def get_products(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    products = Product.query.filter_by(restaurant_id=restaurant.id).all()
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "stock": p.stock,
            "image": p.image,
        }
        for p in products
    ])


@api_bp.route("/orders/<int:order_id>/status")
@login_required
def order_status(order_id):
    order = Order.query.get_or_404(order_id)
    # Seul le propriétaire ou un admin peut voir
    if order.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Non autorisé"}), 403
    return jsonify({"id": order.id, "status": order.status})
