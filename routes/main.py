import math
from flask import Blueprint, render_template, request, jsonify
from models.restaurant import Restaurant, CATEGORIES
from models.order import Order
from models.user import User
from models.review import Review
from extensions import db

main_bp = Blueprint("main", __name__)


def _ratings_map(restaurant_ids):
    """Retourne {restaurant_id: note_moyenne} pour un ensemble de restaurants."""
    if not restaurant_ids:
        return {}
    rows = (
        db.session.query(Review.restaurant_id, db.func.avg(Review.rating))
        .filter(Review.restaurant_id.in_(restaurant_ids))
        .group_by(Review.restaurant_id)
        .all()
    )
    return {rid: round(avg, 1) for rid, avg in rows}


@main_bp.route("/")
def home():
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    ratings = _ratings_map([r.id for r in restaurants])
    return render_template("home.html", restaurants=restaurants, restaurant_ratings=ratings)


@main_bp.route("/restaurants")
def restaurants():
    cat = request.args.get("cat", "all")
    if cat and cat != "all" and cat in CATEGORIES:
        restaurants = Restaurant.query.filter_by(is_active=True, category=cat).all()
    else:
        restaurants = Restaurant.query.filter_by(is_active=True).all()
    ratings = _ratings_map([r.id for r in restaurants])
    return render_template("restaurants.html", restaurants=restaurants,
                           active_cat=cat, categories=CATEGORIES, restaurant_ratings=ratings)


@main_bp.route("/restaurant/<int:restaurant_id>")
def restaurant_menu(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    products = [p for p in restaurant.products if p.stock > 0]
    reviews = (
        Review.query.filter_by(restaurant_id=restaurant_id)
        .order_by(Review.created_at.desc()).limit(20).all()
    )
    rating_avg = _ratings_map([restaurant_id]).get(restaurant_id)
    return render_template("restaurant_menu.html", restaurant=restaurant, products=products,
                           reviews=reviews, rating_avg=rating_avg)


@main_bp.route("/cgu")
def cgu():
    return render_template("cgu.html")


@main_bp.route("/access")
def access_page():
    total_restaurants = Restaurant.query.filter_by(is_active=True).count()
    total_orders      = Order.query.count()
    total_clients     = User.query.filter_by(role="client").count()
    total_revenue     = sum(o.total_amount or 0 for o in Order.query.all())
    # Stats par catégorie
    cat_stats = {
        cat: Restaurant.query.filter_by(is_active=True, category=cat).count()
        for cat in CATEGORIES
    }
    return render_template(
        "access_page.html",
        total_restaurants=total_restaurants,
        total_orders=total_orders,
        total_clients=total_clients,
        total_revenue=total_revenue,
        cat_stats=cat_stats,
        categories=CATEGORIES,
    )


@main_bp.route("/api/restaurants/nearby")
def restaurants_nearby():
    try:
        lat    = float(request.args.get("lat", 0))
        lng    = float(request.args.get("lng", 0))
        radius = float(request.args.get("radius", 10))
        cat    = request.args.get("cat", "all")
    except (ValueError, TypeError):
        return jsonify({"error": "Paramètres invalides"}), 400

    query = Restaurant.query.filter_by(is_active=True)
    if cat != "all" and cat in CATEGORIES:
        query = query.filter_by(category=cat)

    result = []
    for r in query.all():
        if r.latitude is None or r.longitude is None:
            result.append({"id": r.id, "name": r.name, "category": r.category,
                           "category_label": r.category_label, "category_icon": r.category_icon,
                           "distance_km": None})
        else:
            dlat = math.radians(r.latitude - lat)
            dlng = math.radians(r.longitude - lng)
            a = (math.sin(dlat/2)**2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(r.latitude)) *
                 math.sin(dlng/2)**2)
            dist = 6371 * 2 * math.asin(math.sqrt(a))
            if dist <= radius:
                result.append({"id": r.id, "name": r.name, "category": r.category,
                               "category_label": r.category_label, "category_icon": r.category_icon,
                               "distance_km": round(dist, 2)})

    result.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 0))
    return jsonify(result)
