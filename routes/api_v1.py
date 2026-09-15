"""
API REST v1 — JSON + JWT, pensée pour l'app mobile (PWA avancée aujourd'hui,
app native React Native/Flutter demain) et tout futur client tiers.
Indépendante des routes web (session/Jinja2) : mêmes services métier réutilisés.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models.user import User
from models.restaurant import Restaurant, CATEGORIES
from models.product import Product
from models.order import Order
from models.order_item import OrderItem
from models.driver import Driver
from models.review import Review
from services.cart_service import CartService
from services.promo_service import PromoService
from utils.delivery import calculate_delivery_fee
from utils.security import validate_email, sanitize_string

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _err(msg, code=400):
    return jsonify({"error": msg}), code


# ── Auth ────────────────────────────────────────────────────────────────────

@api_v1.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = sanitize_string(data.get("name", ""), 100)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone = sanitize_string(data.get("phone", ""), 50)

    if not name or not email or not password:
        return _err("name, email et password sont requis.")
    if not validate_email(email):
        return _err("Email invalide.")
    if len(password) < 6:
        return _err("Le mot de passe doit contenir au moins 6 caractères.")
    if User.query.filter_by(email=email).first():
        return _err("Cet email est déjà utilisé.", 409)

    user = User(name=name, email=email, phone=phone,
               password=generate_password_hash(password), role="client")
    db.session.add(user)
    db.session.commit()
    return jsonify(_auth_payload(user)), 201


@api_v1.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return _err("Email ou mot de passe incorrect.", 401)

    return jsonify(_auth_payload(user))


@api_v1.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=identity)})


def _auth_payload(user):
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity),
        "refresh_token": create_refresh_token(identity=identity),
        "user": _user_dict(user),
    }


def _user_dict(user):
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "phone": user.phone, "role": user.role,
    }


def _current_user():
    uid = get_jwt_identity()
    return User.query.get(int(uid)) if uid else None


# ── Restaurants / produits ───────────────────────────────────────────────────

@api_v1.route("/restaurants")
def list_restaurants():
    cat = request.args.get("cat", "all")
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)

    q = Restaurant.query.filter_by(is_active=True)
    if cat != "all" and cat in CATEGORIES:
        q = q.filter_by(category=cat)
    restaurants = q.all()

    items = []
    for r in restaurants:
        distance = None
        if lat is not None and lng is not None and r.latitude and r.longitude:
            distance, _ = calculate_delivery_fee(r, lat, lng)
        items.append({
            "id": r.id, "name": r.name, "description": r.description,
            "image": r.image, "address": r.address, "category": r.category,
            "category_label": r.category_label, "category_icon": r.category_icon,
            "distance_km": distance,
            "rating_avg": _restaurant_rating(r.id),
        })
    if lat is not None and lng is not None:
        items.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 0))
    return jsonify(items)


def _restaurant_rating(restaurant_id):
    reviews = Review.query.filter_by(restaurant_id=restaurant_id).all()
    if not reviews:
        return None
    return round(sum(r.rating for r in reviews) / len(reviews), 1)


@api_v1.route("/restaurants/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    r = Restaurant.query.get_or_404(restaurant_id)
    products = [p for p in r.products if p.stock > 0]
    return jsonify({
        "id": r.id, "name": r.name, "description": r.description,
        "image": r.image, "address": r.address, "category": r.category,
        "rating_avg": _restaurant_rating(r.id),
        "products": [_product_dict(p) for p in products],
    })


def _product_dict(p):
    return {
        "id": p.id, "name": p.name, "description": p.description,
        "price": p.price, "stock": p.stock, "image": p.image,
        "has_video": p.has_video, "video_embed_url": p.video_embed_url,
    }


# ── Panier (basé sur la session Flask, comme le site web) ───────────────────

@api_v1.route("/cart", methods=["GET"])
@jwt_required()
def get_cart():
    from flask import session
    cart = CartService.get_cart(session)
    return jsonify({"items": cart, "subtotal": CartService.total(session)})


@api_v1.route("/cart/add", methods=["POST"])
@jwt_required()
def add_to_cart():
    from flask import session
    data = request.get_json(silent=True) or {}
    product = Product.query.get_or_404(data.get("product_id"))
    CartService.add(session, product)
    return jsonify({"ok": True, "subtotal": CartService.total(session)})


@api_v1.route("/cart/clear", methods=["POST"])
@jwt_required()
def clear_cart():
    from flask import session
    CartService.clear(session)
    return jsonify({"ok": True})


# ── Codes promo ───────────────────────────────────────────────────────────────

@api_v1.route("/promo/validate", methods=["POST"])
@jwt_required()
def validate_promo():
    user = _current_user()
    data = request.get_json(silent=True) or {}
    promo, error = PromoService.validate(
        data.get("code", ""), user.id, data.get("restaurant_id"), float(data.get("subtotal", 0)),
    )
    if error:
        return _err(error)
    return jsonify({
        "code": promo.code,
        "discount": promo.compute_discount(float(data.get("subtotal", 0))),
    })


# ── Commandes ─────────────────────────────────────────────────────────────────

@api_v1.route("/orders", methods=["GET"])
@jwt_required()
def my_orders():
    user = _current_user()
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    return jsonify([_order_dict(o) for o in orders])


@api_v1.route("/orders/<int:order_id>", methods=["GET"])
@jwt_required()
def order_detail(order_id):
    user = _current_user()
    order = Order.query.get_or_404(order_id)
    if order.user_id != user.id and not user.is_admin:
        return _err("Non autorisé.", 403)
    return jsonify(_order_dict(order, detailed=True))


def _order_dict(o, detailed=False):
    data = {
        "id": o.id, "status": o.status, "total_amount": o.total_amount,
        "subtotal": o.subtotal, "delivery_fee": o.delivery_fee,
        "discount_amount": o.discount_amount, "payment_status": o.payment_status,
        "restaurant_name": o.restaurant.name if o.restaurant else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "driver": None,
    }
    if o.driver:
        data["driver"] = {
            "id": o.driver.id, "name": o.driver.user.name,
            "phone": o.driver.phone, "vehicle_type": o.driver.vehicle_type,
            "lat": o.driver.current_lat, "lng": o.driver.current_lng,
            "rating_avg": o.driver.rating_avg,
        }
    if detailed:
        data["items"] = [{
            "product_name": it.product.name if it.product else None,
            "quantity": it.quantity, "price": it.price, "subtotal": it.subtotal,
        } for it in o.items]
        data["delivery_address"] = o.delivery_address
        data["delivery_name"] = o.delivery_name
        data["delivery_phone"] = o.delivery_phone
    return data
