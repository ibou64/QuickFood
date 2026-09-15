"""Avis clients sur restaurants et livreurs."""
from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.order import Order
from models.review import Review, DriverReview
from utils.helpers import client_required
from utils.security import sanitize_string

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews")


@reviews_bp.route("/order/<int:order_id>", methods=["POST"])
@login_required
@client_required
def submit_review(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Non autorisé.", "danger")
        return redirect(url_for("client.orders"))
    if order.status != "Livrée":
        flash("Vous ne pouvez noter qu'une commande livrée.", "warning")
        return redirect(url_for("client.orders"))

    try:
        rating = int(request.form.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0
    if not 1 <= rating <= 5:
        flash("Merci de choisir une note entre 1 et 5.", "warning")
        return redirect(url_for("client.orders"))

    comment = sanitize_string(request.form.get("comment", ""), 1000)

    existing = Review.query.filter_by(user_id=current_user.id, order_id=order.id).first()
    if existing:
        existing.rating, existing.comment = rating, comment
    else:
        db.session.add(Review(
            user_id=current_user.id, restaurant_id=order.restaurant_id,
            order_id=order.id, rating=rating, comment=comment,
        ))

    # Avis livreur optionnel, dans le même formulaire
    driver_rating = request.form.get("driver_rating")
    if driver_rating and order.driver_id:
        try:
            dr = int(driver_rating)
            if 1 <= dr <= 5:
                existing_dr = DriverReview.query.filter_by(user_id=current_user.id, order_id=order.id).first()
                if existing_dr:
                    existing_dr.rating = dr
                else:
                    db.session.add(DriverReview(
                        user_id=current_user.id, driver_id=order.driver_id,
                        order_id=order.id, rating=dr,
                    ))
                driver = order.driver
                all_ratings = [r.rating for r in driver.reviews] + [dr]
                driver.rating_avg = round(sum(all_ratings) / len(all_ratings), 2)
                driver.rating_count = len(all_ratings)
        except ValueError:
            pass

    db.session.commit()
    flash("Merci pour votre avis ! ⭐", "success")
    return redirect(url_for("client.orders"))


@reviews_bp.route("/restaurant/<int:restaurant_id>")
def restaurant_reviews(restaurant_id):
    """Fragment JSON utilisé par la page menu pour afficher les avis."""
    reviews = (
        Review.query.filter_by(restaurant_id=restaurant_id)
        .order_by(Review.created_at.desc()).limit(30).all()
    )
    return jsonify([{
        "user": r.user.name,
        "rating": r.rating,
        "comment": r.comment,
        "date": r.created_at.strftime("%d/%m/%Y"),
        "reply": r.reply,
    } for r in reviews])
