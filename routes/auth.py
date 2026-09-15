from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from extensions import db
from utils.security import (check_login_rate_limit, record_login_attempt,
                             reset_login_attempts, sanitize_string, validate_email)
from models.user import User
from models.partner import Partner
from models.restaurant import Restaurant, CATEGORIES

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user     = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Email ou mot de passe incorrect.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=request.form.get("remember") == "on")
        next_page = request.args.get("next")
        return redirect(next_page) if next_page else _redirect_by_role(user)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not request.form.get("accept_cgu"):
            flash("Vous devez accepter les CGU pour créer un compte.", "danger")
            return redirect(url_for("auth.register"))
        if not name or not email or not password:
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("auth.register"))
        if password != confirm:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for("auth.register"))
        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for("auth.register"))

        user = User(
            name=name, email=email,
            password=generate_password_hash(password),
            role="client", created_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Compte créé avec succès !", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/register.html")


@auth_bp.route("/partner/register", methods=["GET", "POST"])
def partner_register():
    # Partenaire ou admin déjà connecté → aller au dashboard
    if current_user.is_authenticated and current_user.role in ("partner", "admin"):
        flash("Vous avez déjà un compte partenaire.", "info")
        return _redirect_by_role(current_user)
    # Client connecté ou non connecté → afficher le formulaire

    if request.method == "POST":
        categories = request.form.getlist("categories")
        valid_cats = [c for c in categories if c in CATEGORIES]

        if not valid_cats:
            flash("Sélectionnez au moins un type de commerce.", "danger")
            return redirect(url_for("auth.partner_register"))

        # ── Cas 1 : client déjà connecté → upgrade son compte ──
        if current_user.is_authenticated and current_user.role == "client":
            name  = current_user.name
            email = current_user.email
            phone = request.form.get("phone", "").strip()

            # Vérifier noms commerces
            commerce_names = {}
            for cat in valid_cats:
                nom = request.form.get(f"name_{cat}", "").strip()
                if not nom:
                    flash(f"Veuillez saisir le nom de votre {CATEGORIES[cat]['label']}.", "danger")
                    return redirect(url_for("auth.partner_register"))
                commerce_names[cat] = nom

            # Upgrade rôle
            current_user.role = "partner"
            db.session.flush()

            # Créer profil Partner
            partner = Partner(name=name, email=email, phone=phone, user_id=current_user.id)
            db.session.add(partner)
            db.session.flush()

            for cat in valid_cats:
                restaurant = Restaurant(
                    name=commerce_names[cat], category=cat,
                    partner_id=partner.id, owner_id=current_user.id,
                )
                db.session.add(restaurant)

            db.session.commit()
            labels = [CATEGORIES[c]["icon"]+" "+CATEGORIES[c]["label"] for c in valid_cats]
            flash(f"Compte partenaire activé ! Commerces : {', '.join(labels)}.", "success")
            return redirect(url_for("partner.dashboard"))

        # ── Cas 2 : nouvel utilisateur (non connecté) ──
        name     = request.form.get("name", "").strip()
        phone    = request.form.get("phone", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # Validations
        if not request.form.get("accept_cgu"):
            flash("Vous devez accepter les CGU Partenaires pour créer votre compte.", "danger")
            return redirect(url_for("auth.partner_register"))
        if not name or not email or not password:
            flash("Nom, email et mot de passe sont obligatoires.", "danger")
            return redirect(url_for("auth.partner_register"))
        if password != confirm:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for("auth.partner_register"))
        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
            return redirect(url_for("auth.partner_register"))
        if not valid_cats:  # déjà vérifié mais garde la cohérence
            flash("Sélectionnez au moins un type de commerce.", "danger")
            return redirect(url_for("auth.partner_register"))
        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for("auth.partner_register"))

        # Vérifier les noms des commerces sélectionnés
        commerce_names = {}
        for cat in valid_cats:
            nom = request.form.get(f"name_{cat}", "").strip()
            if not nom:
                flash(f"Veuillez saisir le nom de votre {CATEGORIES[cat]['label']}.", "danger")
                return redirect(url_for("auth.partner_register"))
            commerce_names[cat] = nom

        # ── Création compte ─────────────────────────────────
        user = User(
            name=name, email=email,
            password=generate_password_hash(password),
            role="partner", created_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.flush()

        partner = Partner(
            name=name, email=email,
            phone=phone, user_id=user.id,
        )
        db.session.add(partner)
        db.session.flush()

        # ── Créer un commerce pour chaque type sélectionné ──
        for cat in valid_cats:
            restaurant = Restaurant(
                name=commerce_names[cat],
                category=cat,
                partner_id=partner.id,
                owner_id=user.id,
            )
            db.session.add(restaurant)

        db.session.commit()
        login_user(user)

        # Message récapitulatif
        labels = [CATEGORIES[c]["icon"] + " " + CATEGORIES[c]["label"] for c in valid_cats]
        flash(
            f"Compte partenaire créé ! Commerces enregistrés : {', '.join(labels)}. "
            "Complétez vos informations depuis le dashboard.",
            "success"
        )
        return redirect(url_for("partner.dashboard"))

    return render_template("partner_register.html")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _redirect_by_role(user):
    role_map = {
        "admin":   "admin.dashboard",
        "partner": "partner.dashboard",
        "driver":  "driver.dashboard",
        "client":  "main.home",
    }
    return redirect(url_for(role_map.get(user.role, "main.home")))
