from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models.restaurant import Restaurant
from models.product import Product
from models.order import Order
from utils.helpers import partner_required, save_uploaded_image, save_uploaded_video, normalize_video_url


def _save_base64_image(data_url: str) -> str | None:
    """Sauvegarde une image base64 (photo caméra) dans static/uploads."""
    import base64, uuid, os
    from flask import current_app
    try:
        # data:image/jpeg;base64,XXXX
        header, encoded = data_url.split(",", 1)
        ext = header.split("/")[1].split(";")[0].lower()
        if ext not in {"jpeg", "jpg", "png", "webp", "gif"}:
            ext = "jpg"
        filename    = f"{uuid.uuid4().hex}.{ext}"
        upload_dir  = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        img_bytes   = base64.b64decode(encoded)
        with open(os.path.join(upload_dir, filename), "wb") as f:
            f.write(img_bytes)
        return filename
    except Exception:
        return None

partner_bp = Blueprint("partner", __name__, url_prefix="/partner")


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

@partner_bp.route("/dashboard")
@login_required
@partner_required
def dashboard():
    partner = current_user.partner
    if not partner:
        flash("Profil partenaire introuvable.", "danger")
        return redirect(url_for("main.home"))

    restaurants = Restaurant.query.filter_by(partner_id=partner.id).all()

    # Statistiques rapides
    total_orders = 0
    total_revenue = 0.0
    for r in restaurants:
        orders = Order.query.filter_by(restaurant_id=r.id).all()
        total_orders += len(orders)
        # FIX: or 0 pour éviter crash si total_amount est None
        total_revenue += sum(o.total_amount or 0 for o in orders if o.status not in ("Annulée",))

    return render_template(
        "partner_dashboard.html",
        restaurants=restaurants,
        total_orders=total_orders,
        total_revenue=total_revenue,
    )


# ──────────────────────────────────────────────
# Restaurants
# ──────────────────────────────────────────────

@partner_bp.route("/restaurants")
@login_required
@partner_required
def restaurants():
    partner = current_user.partner
    restaurants = Restaurant.query.filter_by(partner_id=partner.id).all()
    return render_template("partner_restaurants.html", restaurants=restaurants)


@partner_bp.route("/restaurant/add", methods=["GET", "POST"])
@login_required
@partner_required
def add_restaurant():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Le nom du restaurant est obligatoire.", "danger")
            return redirect(request.url)

        category = request.form.get('category','restaurant')
        restaurant = Restaurant(
            name=name,
            description=description,
            address=address,
            category=category,
            partner_id=current_user.partner.id,
            owner_id=current_user.id,
        )
        # Géolocalisation optionnelle
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

        filename = save_uploaded_image(request.files.get("image"))
        if filename:
            restaurant.image = filename

        db.session.add(restaurant)
        db.session.commit()
        flash("Restaurant ajouté avec succès !", "success")
        return redirect(url_for("partner.dashboard"))

    return render_template("partner_add_restaurant.html")


@partner_bp.route("/restaurant/<int:restaurant_id>/edit", methods=["GET", "POST"])
@login_required
@partner_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    _check_restaurant_ownership(restaurant)

    if request.method == "POST":
        restaurant.name = request.form.get("name", restaurant.name).strip()
        restaurant.description = request.form.get("description", "").strip()
        restaurant.address = request.form.get("address", "").strip()

        filename = save_uploaded_image(request.files.get("image"))
        if filename:
            restaurant.image = filename

        db.session.commit()
        flash("Restaurant mis à jour avec succès.", "success")
        return redirect(url_for("partner.dashboard"))

    return render_template("partner_edit_restaurant.html", restaurant=restaurant)


@partner_bp.route("/restaurant/<int:restaurant_id>/delete", methods=["POST"])
@login_required
@partner_required
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    _check_restaurant_ownership(restaurant)

    db.session.delete(restaurant)
    db.session.commit()
    flash("Restaurant supprimé.", "success")
    return redirect(url_for("partner.dashboard"))


# ──────────────────────────────────────────────
# Produits
# ──────────────────────────────────────────────

@partner_bp.route("/restaurant/<int:restaurant_id>/products")
@login_required
@partner_required
def products(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    _check_restaurant_ownership(restaurant)

    products = Product.query.filter_by(restaurant_id=restaurant.id)\
                            .order_by(Product.id.desc()).all()
    return render_template(
        "partner_restaurant_products.html",
        restaurant=restaurant,
        products=products,
        total_products=len(products),
        total_value=sum(p.price for p in products),
    )


@partner_bp.route("/restaurant/<int:restaurant_id>/product/add", methods=["GET", "POST"])
@login_required
@partner_required
def add_product(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    _check_restaurant_ownership(restaurant)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "")
        stock_raw = request.form.get("stock", "0")

        if not name or not price_raw:
            flash("Nom et prix sont obligatoires.", "danger")
            return redirect(request.url)

        try:
            price = float(price_raw)
            stock = int(stock_raw) if stock_raw else 0
        except ValueError:
            flash("Prix ou stock invalide.", "danger")
            return redirect(request.url)

        product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            restaurant_id=restaurant.id,
        )

        # Priorité 1 : photo prise par la caméra (base64)
        image_data = request.form.get("image_data", "").strip()
        if image_data and image_data.startswith("data:image"):
            filename = _save_base64_image(image_data)
            if filename:
                product.image = filename
        else:
            # Priorité 2 : fichier uploadé depuis la galerie
            filename = save_uploaded_image(request.files.get("image"))
            if filename:
                product.image = filename

        # Vidéo : fichier uploadé
        vid_file = save_uploaded_video(request.files.get("video"))
        if vid_file:
            product.video_file = vid_file
        # Vidéo : lien externe
        vid_url = normalize_video_url(request.form.get("video_url", ""))
        if vid_url:
            product.video_url = vid_url

        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté avec succès.", "success")
        return redirect(url_for("partner.products", restaurant_id=restaurant.id))

    return render_template("partner_add_product.html", restaurant=restaurant)


@partner_bp.route("/product/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@partner_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    _check_restaurant_ownership(product.restaurant)

    if request.method == "POST":
        product.name = request.form.get("name", product.name).strip()
        product.description = request.form.get("description", "").strip()
        try:
            product.price = float(request.form.get("price", product.price))
            product.stock = int(request.form.get("stock", product.stock))
        except ValueError:
            flash("Prix ou stock invalide.", "danger")
            return redirect(request.url)

        image_data = request.form.get("image_data", "").strip()
        if image_data and image_data.startswith("data:image"):
            filename = _save_base64_image(image_data)
            if filename:
                product.image = filename
        else:
            filename = save_uploaded_image(request.files.get("image"))
            if filename:
                product.image = filename

        # Vidéo : fichier uploadé
        vid_file = save_uploaded_video(request.files.get("video"))
        if vid_file:
            product.video_file = vid_file
        # Vidéo : lien externe (écrase l ancien si renseigné)
        vid_url_raw = request.form.get("video_url", "").strip()
        if vid_url_raw:
            product.video_url = normalize_video_url(vid_url_raw)
        # Supprimer vidéo si demandé
        if request.form.get("remove_video"):
            product.video_file = None
            product.video_url  = None

        db.session.commit()
        flash("Produit modifié avec succès.", "success")
        return redirect(url_for("partner.products", restaurant_id=product.restaurant_id))

    return render_template("partner_edit_product.html", product=product)


@partner_bp.route("/product/<int:product_id>/delete", methods=["POST"])
@login_required
@partner_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    _check_restaurant_ownership(product.restaurant)

    restaurant_id = product.restaurant_id
    db.session.delete(product)
    db.session.commit()
    flash("Produit supprimé.", "success")
    return redirect(url_for("partner.products", restaurant_id=restaurant_id))


# ──────────────────────────────────────────────
# Profil partenaire
# ──────────────────────────────────────────────

@partner_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
@partner_required
def edit_profile():
    from werkzeug.security import generate_password_hash, check_password_hash

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email:
            flash("Nom et email obligatoires.", "warning")
            return redirect(url_for("partner.edit_profile"))

        if password and password != confirm:
            flash("Les mots de passe ne correspondent pas.", "warning")
            return redirect(url_for("partner.edit_profile"))

        from models.user import User
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash("Cet email est déjà utilisé.", "warning")
            return redirect(url_for("partner.edit_profile"))

        current_user.name = name
        current_user.email = email
        if password:
            current_user.password = generate_password_hash(password)

        db.session.commit()
        flash("Profil mis à jour avec succès !", "success")
        return redirect(url_for("partner.dashboard"))

    return render_template("edit_partner.html", user=current_user)


# ──────────────────────────────────────────────
# Helper interne
# ──────────────────────────────────────────────

def _check_restaurant_ownership(restaurant):
    """Redirige si le partenaire connecté ne possède pas ce restaurant."""
    partner = current_user.partner
    if not partner or restaurant.partner_id != partner.id:
        flash("Accès non autorisé.", "danger")
        from flask import abort
        abort(403)


# ──────────────────────────────────────────────
# Revenus & Split Payment (vue partenaire)
# ──────────────────────────────────────────────

@partner_bp.route("/revenus")
@login_required
@partner_required
def revenus():
    """
    Tableau de bord des revenus : le partenaire voit exactement
    ce que chaque restaurant lui doit après déduction de la commission QuickFood.
    """
    from datetime import datetime, timedelta
    from services.split_service import SplitService

    partner = current_user.partner
    if not partner:
        flash("Profil partenaire introuvable.", "danger")
        return redirect(url_for("partner.dashboard"))

    period    = request.args.get("period", "month")
    now       = datetime.utcnow()
    date_from = (now - timedelta(days=30) if period == "month" else
                 now - timedelta(days=7)  if period == "week"  else None)

    restaurants = Restaurant.query.filter_by(partner_id=partner.id).all()

    rows           = []
    grand_total    = 0.0
    grand_net      = 0.0
    grand_comm     = 0.0
    grand_delivery = 0.0

    for r in restaurants:
        q = Order.query.filter_by(
            restaurant_id=r.id
        ).filter(Order.payment_status == "success")
        if date_from:
            q = q.filter(Order.created_at >= date_from)
        ords = q.order_by(Order.created_at.desc()).all()

        total    = sum(o.total_amount      or 0 for o in ords)
        delivery = sum(o.delivery_fee      or 0 for o in ords)
        comm     = sum(o.commission_amount or 0 for o in ords if o.split_status == "done")
        net      = sum(o.restaurant_amount or 0 for o in ords if o.split_status == "done")
        pending  = [o for o in ords if o.split_status != "done"]

        rows.append({
            "restaurant": r,
            "nb_orders":  len(ords),
            "total":      total,
            "delivery":   delivery,
            "commission": comm,
            "net":        net,
            "pending":    len(pending),
            "orders":     ords,
        })
        grand_total    += total
        grand_net      += net
        grand_comm     += comm
        grand_delivery += delivery

    return render_template(
        "partner_revenus.html",
        rows=rows,
        period=period,
        grand_total=grand_total,
        grand_net=grand_net,
        grand_comm=grand_comm,
        grand_delivery=grand_delivery,
    )
