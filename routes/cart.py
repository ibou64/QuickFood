from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user

from models.product import Product
from models.restaurant import Restaurant
from services.cart_service import CartService
from services.order_service import OrderService
from services.promo_service import PromoService
from utils.delivery import calculate_delivery_fee, DEFAULT_FEE

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/cart/add/<int:product_id>")
@login_required
def add(product_id):
    product = Product.query.get_or_404(product_id)
    cart = CartService.get_cart(session)
    if cart:
        existing_restaurant_id = list(cart.values())[0].get("restaurant_id")
        if existing_restaurant_id and existing_restaurant_id != product.restaurant_id:
            flash("Votre panier contient des articles d'un autre restaurant. Videz-le d'abord.", "warning")
            return redirect(request.referrer or url_for("main.home"))
    CartService.add(session, product)
    flash(f"« {product.name} » ajouté au panier ✅", "success")
    return redirect(request.referrer or url_for("main.home"))


@cart_bp.route("/cart")
@login_required
def view():
    cart = CartService.get_cart(session)
    subtotal = CartService.total(session)
    discount, promo_code = 0, session.get("promo_code")
    if cart and promo_code:
        restaurant_id = list(cart.values())[0].get("restaurant_id")
        promo, error = PromoService.validate(promo_code, current_user.id, restaurant_id, subtotal)
        if promo:
            discount = promo.compute_discount(subtotal)
        else:
            session.pop("promo_code", None)  # code devenu invalide entre-temps
    total = (subtotal + DEFAULT_FEE - discount) if cart else 0
    return render_template("cart.html", cart=cart, subtotal=subtotal,
                           total=total, delivery_fee=DEFAULT_FEE,
                           discount=discount, promo_code=promo_code if discount else None)


@cart_bp.route("/cart/apply-promo", methods=["POST"])
@login_required
def apply_promo():
    code = (request.form.get("promo_code") or "").strip()
    cart = CartService.get_cart(session)
    if not cart:
        flash("Votre panier est vide.", "warning")
        return redirect(url_for("cart.view"))

    restaurant_id = list(cart.values())[0].get("restaurant_id")
    subtotal = CartService.total(session)
    promo, error = PromoService.validate(code, current_user.id, restaurant_id, subtotal)
    if error:
        flash(error, "danger")
    else:
        session["promo_code"] = promo.code
        flash(f"Code {promo.code} appliqué 🎉", "success")
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/remove-promo", methods=["POST"])
@login_required
def remove_promo():
    session.pop("promo_code", None)
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/increase/<int:product_id>")
@login_required
def increase(product_id):
    CartService.increase(session, product_id)
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/decrease/<int:product_id>")
@login_required
def decrease(product_id):
    CartService.decrease(session, product_id)
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/remove/<int:product_id>")
@login_required
def remove(product_id):
    CartService.remove(session, product_id)
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/clear")
@login_required
def clear():
    CartService.clear(session)
    flash("Panier vidé.", "info")
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/delivery-fee")
@login_required
def delivery_fee_preview():
    """AJAX — aperçu frais de livraison selon position client."""
    from flask import jsonify
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    restaurant_id = request.args.get("restaurant_id", type=int)

    restaurant = Restaurant.query.get(restaurant_id) if restaurant_id else None
    distance, fee = calculate_delivery_fee(restaurant, lat, lng)

    return jsonify({
        "distance": distance,
        "fee": fee,
        "fee_display": f"{fee:,} FCFA".replace(",", " "),
        "label": f"{distance:.1f} km" if distance else "N/A",
    })


@cart_bp.route("/confirm-order", methods=["GET", "POST"])
@login_required
def confirm_order():
    cart = CartService.get_cart(session)
    if not cart:
        flash("Votre panier est vide.", "warning")
        return redirect(url_for("cart.view"))

    subtotal = CartService.total(session)

    # Récupérer le restaurant
    restaurant = None
    try:
        restaurant_id = list(cart.values())[0].get("restaurant_id")
        if restaurant_id:
            restaurant = Restaurant.query.get(restaurant_id)
    except Exception:
        pass

    # Calcul frais par défaut (sans GPS)
    _, delivery_fee = calculate_delivery_fee(restaurant, None, None)
    discount, promo_code = 0, session.get("promo_code")
    if promo_code and restaurant:
        promo, error = PromoService.validate(promo_code, current_user.id, restaurant.id, subtotal)
        discount = promo.compute_discount(subtotal) if promo else 0
    total = subtotal + delivery_fee - discount

    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        phone   = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        lat     = request.form.get("delivery_lat") or None
        lng     = request.form.get("delivery_lng") or None

        if not name or not phone or not address:
            flash("Veuillez remplir tous les champs de livraison.", "danger")
            return redirect(url_for("cart.confirm_order"))

        try:
            order = OrderService.create_from_cart(
                session,
                user_id=current_user.id,
                delivery_name=name,
                delivery_phone=phone,
                delivery_address=address,
                delivery_latitude=float(lat) if lat else None,
                delivery_longitude=float(lng) if lng else None,
                promo_code=session.get("promo_code"),
            )
            session.pop("promo_code", None)

            # Redirection selon mode de paiement
            payment_method = request.form.get("payment_method", "cash")
            if payment_method == "online":
                return redirect(url_for("payment.pay", order_id=order.id))

            flash(f"Commande #{order.id} confirmée ! Paiement à la livraison. 🎉", "success")
            return redirect(url_for("client.orders"))

        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("cart.view"))

    return render_template("confirm_order.html", cart=cart,
                           subtotal=subtotal, total=total,
                           delivery_fee=delivery_fee, restaurant=restaurant,
                           discount=discount, promo_code=promo_code if discount else None)
