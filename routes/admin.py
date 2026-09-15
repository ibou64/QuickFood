from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
import csv, io
from datetime import datetime, timedelta

from extensions import db
from models.user import User
from models.partner import Partner
from models.restaurant import Restaurant
from models.product import Product
from models.order import Order
from models.driver import Driver
from models.promo import PromoCode
from models.review import Review
from services.order_service import OrderService
from utils.helpers import admin_required, save_uploaded_image

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

TVA_RATE = 0.18  # 18 % TVA Sénégal


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    total_clients = User.query.filter_by(role="client").count()
    total_partners = Partner.query.count()
    total_restaurants = Restaurant.query.count()
    total_orders = Order.query.count()
    total_revenue = sum(o.total_amount or 0 for o in Order.query.all())
    recent_restaurants = Restaurant.query.order_by(Restaurant.created_at.desc()).limit(5).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template(
        "admin_dashboard.html",
        total_clients=total_clients,
        total_partners=total_partners,
        total_restaurants=total_restaurants,
        total_orders=total_orders,
        total_revenue=total_revenue,
        recent_restaurants=recent_restaurants,
        recent_orders=recent_orders,
    )


# ── Restaurants ───────────────────────────────────────────────────────────────

@admin_bp.route("/restaurants")
@login_required
@admin_required
def restaurants():
    restaurants = Restaurant.query.order_by(Restaurant.created_at.desc()).all()
    return render_template("admin_restaurants.html", restaurants=restaurants)


@admin_bp.route("/restaurant/<int:restaurant_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Le nom est obligatoire.", "danger")
            return redirect(request.url)
        restaurant.name = name
        restaurant.description = request.form.get("description", "").strip()
        restaurant.address = request.form.get("address", "").strip()
        try:
            restaurant.commission_rate = float(request.form.get("commission_rate", 10))
        except ValueError:
            restaurant.commission_rate = 10.0
        # Géolocalisation
        try:
            lat = request.form.get("latitude", "").strip()
            restaurant.latitude = float(lat) if lat else None
        except ValueError:
            restaurant.latitude = None
        try:
            lng = request.form.get("longitude", "").strip()
            restaurant.longitude = float(lng) if lng else None
        except ValueError:
            restaurant.longitude = None
        try:
            r = request.form.get("delivery_radius_km", "5").strip()
            restaurant.delivery_radius_km = float(r) if r else 5.0
        except ValueError:
            restaurant.delivery_radius_km = 5.0

        restaurant.is_active = request.form.get("is_active") == "on"
        filename = save_uploaded_image(request.files.get("image"))
        if filename:
            restaurant.image = filename
        db.session.commit()
        flash("Restaurant mis à jour.", "success")
        return redirect(url_for("admin.restaurants"))
    return render_template("admin_edit_restaurant.html", restaurant=restaurant)


@admin_bp.route("/restaurant/<int:restaurant_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    db.session.delete(restaurant)
    db.session.commit()
    flash("Restaurant supprimé.", "success")
    return redirect(url_for("admin.restaurants"))


@admin_bp.route("/restaurant/<int:restaurant_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    restaurant.is_active = not restaurant.is_active
    db.session.commit()
    flash(f"Restaurant {'activé' if restaurant.is_active else 'désactivé'}.", "success")
    return redirect(url_for("admin.restaurants"))


@admin_bp.route("/restaurant/<int:restaurant_id>/orders", methods=["GET", "POST"])
@login_required
@admin_required
def restaurant_orders(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if request.method == "POST":
        order_id = request.form.get("order_id")
        new_status = request.form.get("status")
        if order_id and new_status:
            OrderService.update_status(int(order_id), new_status)
            flash("Statut mis à jour.", "success")
        return redirect(url_for("admin.restaurant_orders", restaurant_id=restaurant.id))
    orders = Order.query.filter_by(restaurant_id=restaurant.id)\
                        .order_by(Order.created_at.desc()).all()
    total_revenue = sum(o.total_amount or 0 for o in orders if o.status == "Livrée")
    commission_rate = restaurant.commission_rate or 0
    platform_commission = total_revenue * (commission_rate / 100)
    restaurant_revenue = total_revenue - platform_commission
    return render_template(
        "admin_restaurant_orders.html",
        restaurant=restaurant,
        orders=orders,
        total_revenue=total_revenue,
        platform_commission=platform_commission,
        restaurant_revenue=restaurant_revenue,
    )


# ── Commandes ─────────────────────────────────────────────────────────────────

@admin_bp.route("/orders")
@login_required
@admin_required
def orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin_orders.html", orders=orders)


@admin_bp.route("/order/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_order(order_id):
    # FIX PRINCIPAL : variable `order` bien définie et transmise au template
    order = Order.query.get_or_404(order_id)
    if request.method == "POST":
        new_status = request.form.get("status")
        if new_status:
            OrderService.update_status(order_id, new_status)
            flash(f"Commande #{order.id} mise à jour.", "success")
        else:
            flash("Statut invalide.", "warning")
        return redirect(url_for("admin.orders"))
    # IMPORTANT : on passe bien `order=order` au template
    return render_template("admin_edit_order.html", order=order)


@admin_bp.route("/order/delete/<int:order_id>", methods=["POST"])
@login_required
@admin_required
def delete_order(order_id):
    try:
        OrderService.delete(order_id)
        flash(f"Commande #{order_id} supprimée.", "success")
    except Exception as e:
        flash(f"Erreur : {str(e)}", "danger")
    return redirect(url_for("admin.orders"))


# ── Partenaires ───────────────────────────────────────────────────────────────

@admin_bp.route("/partners")
@login_required
@admin_required
def partners():
    partners = User.query.filter_by(role="partner").order_by(User.id.desc()).all()
    return render_template("admin_partners.html", partners=partners)


@admin_bp.route("/partner/toggle/<int:partner_id>", methods=["POST"])
@login_required
@admin_required
def toggle_partner(partner_id):
    partner = Partner.query.get_or_404(partner_id)
    data = request.get_json(silent=True) or {}
    partner.is_active = data.get("active", not partner.is_active)
    db.session.commit()
    return jsonify({"success": True, "is_active": partner.is_active})


# ── Utilisateurs ──────────────────────────────────────────────────────────────

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


# ── Statistiques ──────────────────────────────────────────────────────────────

@admin_bp.route("/stats")
@login_required
@admin_required
def stats():
    from sqlalchemy import func
    from models.order_item import OrderItem

    total_users = User.query.filter_by(role="client").count()
    total_partners = User.query.filter_by(role="partner").count()
    total_orders = Order.query.count()
    total_revenue = sum(o.total_amount or 0 for o in Order.query.all())
    pending_orders = Order.query.filter_by(status="En attente").count()
    delivered_orders = Order.query.filter_by(status="Livrée").count()
    cancelled_orders = Order.query.filter_by(status="Annulée").count()

    top_raw = (
        db.session.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("qty"))
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5).all()
    )
    top_products = []
    for product_id, qty in top_raw:
        product = Product.query.get(product_id)
        top_products.append({
            "name": product.name if product else "Produit supprimé",
            "quantity_sold": qty,
        })

    return render_template(
        "admin_stats.html",
        total_users=total_users,
        total_partners=total_partners,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders,
        top_products=top_products,
    )


# ── Commissions & TVA ────────────────────────────────────────────────────────

@admin_bp.route("/commissions")
@login_required
@admin_required
def commissions():
    period        = request.args.get("period", "all")
    restaurant_id = request.args.get("restaurant_id", "", type=str)
    now           = datetime.utcnow()
    date_from     = None
    if period == "month":
        date_from = now - timedelta(days=30)
    elif period == "week":
        date_from = now - timedelta(days=7)

    restaurants = Restaurant.query.order_by(Restaurant.name).all()
    rows = []
    grand_ca = grand_commission = grand_tva = grand_commission_ttc = grand_restaurant = grand_delivery = 0.0
    # Compteurs split
    split_done_count  = 0
    split_pend_count  = 0
    split_total_qf    = 0.0   # total encaissé QuickFood (commission + livraison)

    for r in restaurants:
        if restaurant_id and str(r.id) != restaurant_id:
            continue

        # ── Commandes livrées avec split calculé ─────────────────────────────
        q = Order.query.filter_by(restaurant_id=r.id).filter(
            Order.status.in_(["Livrée", "completed"])
        )
        if date_from:
            q = q.filter(Order.created_at >= date_from)
        ords = q.all()

        # Préférer les montants enregistrés par SplitService si disponibles
        nb = len(ords)
        ca = sum(o.total_amount or 0 for o in ords)
        delivery = sum(o.delivery_fee or 0 for o in ords)

        # Commission : utiliser split_status=done si dispo, sinon recalculer
        split_done = [o for o in ords if o.split_status == "done"]
        split_pend = [o for o in ords if o.split_status != "done"]

        commission_ht  = sum(o.commission_amount or 0 for o in split_done)
        restaurant_net = sum(o.restaurant_amount or 0 for o in split_done)

        # Pour les commandes sans split enregistré, calculer à la volée
        for o in split_pend:
            rate_dec   = (r.commission_rate or 0) / 100
            sub        = o.subtotal or 0
            comm       = round(sub * rate_dec, 2)
            commission_ht  += comm
            restaurant_net += sub - comm

        tva            = round(commission_ht * TVA_RATE, 2)
        commission_ttc = round(commission_ht + tva, 2)
        qf_total       = round(commission_ttc + delivery, 2)  # total QuickFood

        rows.append({
            "id": r.id, "name": r.name,
            "commission_rate": r.commission_rate,
            "nb_orders": nb,
            "ca": ca,
            "delivery": delivery,
            "commission_ht": commission_ht,
            "tva": tva,
            "commission_ttc": commission_ttc,
            "restaurant_net": restaurant_net,
            "qf_total": qf_total,
            "split_done": len(split_done),
            "split_pending": len(split_pend),
        })
        grand_ca             += ca
        grand_commission     += commission_ht
        grand_tva            += tva
        grand_commission_ttc += commission_ttc
        grand_restaurant     += restaurant_net
        grand_delivery       += delivery
        split_done_count     += len(split_done)
        split_pend_count     += len(split_pend)
        split_total_qf       += qf_total

    totals = {
        "ca":             grand_ca,
        "delivery":       grand_delivery,
        "commission_ht":  grand_commission,
        "tva":            grand_tva,
        "commission_ttc": grand_commission_ttc,
        "restaurant_net": grand_restaurant,
        "quickfood_total": round(grand_commission_ttc + grand_delivery, 2),
        "split_done":     split_done_count,
        "split_pending":  split_pend_count,
    }
    return render_template(
        "admin_commissions.html",
        rows=rows, totals=totals,
        restaurants=restaurants, period=period,
        selected_restaurant=restaurant_id,
        tva_rate=int(TVA_RATE * 100),
    )


# ── Split Payment — vue détail par commande ───────────────────────────────────

@admin_bp.route("/splits")
@login_required
@admin_required
def splits():
    """Liste toutes les commandes avec leur split calculé."""
    from services.split_service import SplitService
    period        = request.args.get("period", "month")
    restaurant_id = request.args.get("restaurant_id", "", type=str)
    status_filter = request.args.get("split_status", "")
    now           = datetime.utcnow()
    date_from     = now - timedelta(days=30) if period == "month" else (
                    now - timedelta(days=7)  if period == "week"  else None)

    restaurants = Restaurant.query.order_by(Restaurant.name).all()
    q = Order.query.filter(Order.payment_status == "success")
    if date_from:
        q = q.filter(Order.created_at >= date_from)
    if restaurant_id:
        q = q.filter(Order.restaurant_id == int(restaurant_id))
    if status_filter:
        q = q.filter(Order.split_status == status_filter)
    orders = q.order_by(Order.created_at.desc()).all()

    # Totaux
    total_collected  = sum(o.total_amount      or 0 for o in orders)
    total_commission = sum(o.commission_amount or 0 for o in orders if o.split_status == "done")
    total_delivery   = sum(o.delivery_fee      or 0 for o in orders)
    total_restaurant = sum(o.restaurant_amount or 0 for o in orders if o.split_status == "done")
    pending_count    = sum(1 for o in orders if o.split_status != "done")

    return render_template(
        "admin_splits.html",
        orders=orders,
        restaurants=restaurants,
        period=period,
        selected_restaurant=restaurant_id,
        status_filter=status_filter,
        total_collected=total_collected,
        total_commission=total_commission,
        total_delivery=total_delivery,
        total_restaurant=total_restaurant,
        pending_count=pending_count,
    )


@admin_bp.route("/splits/recalc/<int:order_id>", methods=["POST"])
@login_required
@admin_required
def recalc_split(order_id):
    """Force le recalcul du split pour une commande (utile si raté lors de l'IPN)."""
    from services.split_service import SplitService
    order = Order.query.get_or_404(order_id)
    if order.payment_status != "success":
        flash("Cette commande n'est pas encore payée.", "warning")
        return redirect(url_for("admin.splits"))
    order.split_status = "pending"  # reset pour forcer recalcul
    db.session.commit()
    ok = SplitService.execute(order)
    if ok:
        flash(f"✓ Split recalculé pour la commande #{order.id}", "success")
    else:
        flash(f"Erreur lors du recalcul du split #{order.id}", "danger")
    return redirect(url_for("admin.splits"))


@admin_bp.route("/splits/export")
@login_required
@admin_required
def export_splits():
    """Export CSV des splits par commande."""
    orders = Order.query.filter(
        Order.payment_status == "success"
    ).order_by(Order.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Commande", "Restaurant", "Date", "Total (FCFA)",
        "Sous-total", "Frais livraison", "Taux commission (%)",
        "Commission QuickFood (FCFA)", "Net restaurant (FCFA)",
        "Statut split", "Date split"
    ])
    for o in orders:
        writer.writerow([
            f"#{o.id}",
            o.restaurant.name if o.restaurant else "",
            o.created_at.strftime("%d/%m/%Y %H:%M"),
            int(o.total_amount or 0),
            int(o.subtotal or 0),
            int(o.delivery_fee or 0),
            o.commission_rate or "",
            int(o.commission_amount or 0),
            int(o.restaurant_amount or 0),
            o.split_status,
            o.split_done_at.strftime("%d/%m/%Y %H:%M") if o.split_done_at else "",
        ])
    output.seek(0)
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv;charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=quickfood_splits.csv"}
    )


@admin_bp.route("/commissions/export")
@login_required
@admin_required
def export_commissions():
    """Export CSV des commissions."""
    period = request.args.get("period", "all")
    now = datetime.utcnow()
    date_from = None
    if period == "month":
        date_from = now - timedelta(days=30)
    elif period == "week":
        date_from = now - timedelta(days=7)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Restaurant", "Nb commandes", "CA (FCFA)", "Commission HT",
                     "TVA 18%", "Commission TTC", "Net restaurant"])

    for r in Restaurant.query.order_by(Restaurant.name).all():
        q = Order.query.filter_by(restaurant_id=r.id).filter(
            Order.status.in_(["Livrée", "completed"])
        )
        if date_from:
            q = q.filter(Order.created_at >= date_from)
        ords = q.all()
        ca = sum(o.total_amount or 0 for o in ords)
        rate = (r.commission_rate or 0) / 100
        cht = ca * rate
        tva = cht * TVA_RATE
        writer.writerow([r.name, len(ords), int(ca), int(cht),
                         int(tva), int(cht + tva), int(ca - cht - tva)])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=commissions.csv"}
    )


# ── Livraisons ────────────────────────────────────────────────────────────────

@admin_bp.route("/deliveries")
@login_required
@admin_required
def deliveries():
    from sqlalchemy import func
    from datetime import date

    # Commandes en cours
    active_orders = Order.query.filter(
        Order.status.in_(["En attente", "En préparation", "En livraison"])
    ).order_by(Order.created_at.desc()).all()

    # 30 dernières livrées/annulées
    recent_orders = Order.query.filter(
        Order.status.in_(["Livrée", "Annulée"])
    ).order_by(Order.created_at.desc()).limit(30).all()

    # Stats du jour
    today = datetime.utcnow().date()
    stats_raw = db.session.query(
        func.count(Order.id).label("total_orders"),
        func.sum(Order.delivery_fee).label("total_fees"),
        func.avg(Order.delivery_distance).label("avg_distance"),
    ).filter(
        func.date(Order.created_at) == today
    ).first()

    # Calcul avg_distance à la volée si NULL en base
    avg_dist = stats_raw.avg_distance
    if avg_dist is None:
        from utils.delivery import haversine
        all_today = Order.query.filter(
            func.date(Order.created_at) == today
        ).all()
        distances = []
        for o in all_today:
            if o.delivery_distance:
                distances.append(o.delivery_distance)
            elif (o.delivery_latitude and o.delivery_longitude
                  and o.restaurant and o.restaurant.latitude and o.restaurant.longitude):
                d = haversine(
                    o.restaurant.latitude, o.restaurant.longitude,
                    o.delivery_latitude, o.delivery_longitude
                )
                distances.append(d)
        avg_dist = round(sum(distances)/len(distances), 2) if distances else None

    stats = {
        "total_orders":  stats_raw.total_orders  or 0,
        "total_fees":    stats_raw.total_fees     or 0,
        "avg_distance":  avg_dist,
    }

    return render_template(
        "admin_deliveries.html",
        active_orders=active_orders,
        recent_orders=recent_orders,
        stats=stats,
    )


@admin_bp.route("/delivery/<int:order_id>/status", methods=["POST"])
@login_required
@admin_required
def update_delivery_status(order_id):
    new_status = request.form.get("status")
    if new_status:
        OrderService.update_status(order_id, new_status)
        flash(f"Commande #{order_id} → {new_status}", "success")
    return redirect(url_for("admin.deliveries"))


# ── Livreurs ─────────────────────────────────────────────────────────────────

@admin_bp.route("/drivers")
@login_required
@admin_required
def drivers():
    all_drivers = Driver.query.order_by(Driver.created_at.desc()).all()
    return render_template("admin_drivers.html", drivers=all_drivers)


@admin_bp.route("/drivers/add", methods=["POST"])
@login_required
@admin_required
def add_driver():
    from werkzeug.security import generate_password_hash
    import secrets as _secrets

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    vehicle_type = request.form.get("vehicle_type", "moto")
    plate_number = request.form.get("plate_number", "").strip()

    if not name or not email or not phone:
        flash("Nom, email et téléphone sont obligatoires.", "danger")
        return redirect(url_for("admin.drivers"))
    if User.query.filter_by(email=email).first():
        flash("Cet email est déjà utilisé.", "danger")
        return redirect(url_for("admin.drivers"))

    temp_password = _secrets.token_urlsafe(6)
    user = User(name=name, email=email, phone=phone, role="driver",
               password=generate_password_hash(temp_password))
    db.session.add(user)
    db.session.flush()

    driver = Driver(user_id=user.id, phone=phone, vehicle_type=vehicle_type,
                    plate_number=plate_number)
    db.session.add(driver)
    db.session.commit()

    flash(f"Livreur {name} créé. Mot de passe temporaire : {temp_password} "
         f"(à transmettre puis faire changer).", "success")
    return redirect(url_for("admin.drivers"))


@admin_bp.route("/drivers/<int:driver_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    driver.is_active = not driver.is_active
    if not driver.is_active:
        driver.is_available = False
    db.session.commit()
    flash(f"Livreur {'activé' if driver.is_active else 'désactivé'}.", "success")
    return redirect(url_for("admin.drivers"))


# ── Codes promo ────────────────────────────────────────────────────────────────

@admin_bp.route("/promos")
@login_required
@admin_required
def promos():
    all_promos = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
    restaurants = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.name).all()
    return render_template("admin_promos.html", promos=all_promos, restaurants=restaurants)


@admin_bp.route("/promos/add", methods=["POST"])
@login_required
@admin_required
def add_promo():
    code = request.form.get("code", "").strip().upper()
    if not code:
        flash("Le code est obligatoire.", "danger")
        return redirect(url_for("admin.promos"))
    if PromoCode.query.filter_by(code=code).first():
        flash("Ce code existe déjà.", "danger")
        return redirect(url_for("admin.promos"))

    try:
        discount_value = float(request.form.get("discount_value", 0))
        min_order_amount = float(request.form.get("min_order_amount", 0) or 0)
        max_uses = request.form.get("max_uses") or None
        max_uses = int(max_uses) if max_uses else None
    except ValueError:
        flash("Valeurs numériques invalides.", "danger")
        return redirect(url_for("admin.promos"))

    restaurant_id = request.form.get("restaurant_id") or None

    promo = PromoCode(
        code=code,
        description=request.form.get("description", "").strip(),
        discount_type=request.form.get("discount_type", "percent"),
        discount_value=discount_value,
        min_order_amount=min_order_amount,
        max_uses=max_uses,
        restaurant_id=int(restaurant_id) if restaurant_id else None,
    )
    db.session.add(promo)
    db.session.commit()
    flash(f"Code promo {code} créé.", "success")
    return redirect(url_for("admin.promos"))


@admin_bp.route("/promos/<int:promo_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_promo(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    promo.is_active = not promo.is_active
    db.session.commit()
    flash(f"Code {promo.code} {'activé' if promo.is_active else 'désactivé'}.", "success")
    return redirect(url_for("admin.promos"))


# ── Avis clients ──────────────────────────────────────────────────────────────

@admin_bp.route("/reviews")
@login_required
@admin_required
def reviews():
    all_reviews = Review.query.order_by(Review.created_at.desc()).limit(100).all()
    return render_template("admin_reviews.html", reviews=all_reviews)


@admin_bp.route("/reviews/<int:review_id>/reply", methods=["POST"])
@login_required
@admin_required
def reply_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.reply = request.form.get("reply", "").strip()
    review.replied_at = datetime.utcnow()
    db.session.commit()
    flash("Réponse publiée.", "success")
    return redirect(url_for("admin.reviews"))
