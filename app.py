"""
QuickFood — Application principale
Architecture Blueprint propre, corrigée et optimisée.
"""
import os
from dotenv import load_dotenv
load_dotenv()  # charge .env si présent
from flask import Flask
from config import Config
from extensions import db, login_manager, migrate, socketio, jwt, cors


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Extensions ────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*")
    jwt.init_app(app)
    # API v1 ouverte aux clients mobiles (app native future) + PWA
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # ── User loader ───────────────────────────────────────
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Blueprints ────────────────────────────────────────
    from routes.main          import main_bp
    from routes.auth          import auth_bp
    from routes.cart          import cart_bp
    from routes.client        import client_bp
    from routes.partner       import partner_bp
    from routes.admin         import admin_bp
    from routes.api           import api_bp
    from routes.api_v1        import api_v1
    from routes.payment       import payment_bp
    from routes.support       import support_bp
    from routes.driver        import driver_bp
    from routes.reviews       import reviews_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(partner_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1)
    app.register_blueprint(payment_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(notifications_bp)

    # ── Sockets ───────────────────────────────────────────
    import sockets  # noqa: F401

    # ── Sécurité : headers HTTP + CSRF ───────────────────
    from utils.security import apply_security_headers, generate_csrf_token

    @app.after_request
    def add_security_headers(response):
        return apply_security_headers(response)

    # ── Context processor global ──────────────────────────
    from services.cart_service import CartService
    from flask import session

    @app.context_processor
    def inject_globals():
        return {
            "cart_count": CartService.count(session),
            "csrf_token": generate_csrf_token,
        }

    # ── Filtre format nombre ──────────────────────────────
    @app.template_filter("format_number")
    def format_number(value):
        try:
            return "{:,.0f}".format(float(value)).replace(",", " ")
        except (ValueError, TypeError):
            return value

    # ── Initialisation DB ─────────────────────────────────
    with app.app_context():
        instance_dir = os.path.join(os.path.dirname(__file__), "instance")
        os.makedirs(instance_dir, exist_ok=True)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        # noqa — imports nécessaires pour que db.create_all() connaisse toutes les tables
        from models.support import SupportTicket
        from models.driver import Driver
        from models.review import Review, DriverReview
        from models.promo import PromoCode, PromoRedemption
        from models.notification import Notification
        db.create_all()
        _seed_admin()

    # ── Route Service Worker (doit être à la racine /) ──────
    @app.route("/sw.js")
    def service_worker():
        from flask import send_from_directory
        return send_from_directory(app.static_folder, "sw.js",
                                   mimetype="application/javascript")

    return app


def _seed_admin():
    """Crée le compte admin par défaut s'il n'existe pas."""
    from models.user import User
    from werkzeug.security import generate_password_hash
    from datetime import datetime

    if not User.query.filter_by(email="admin@quickfood.sn").first():
        raw_password = os.environ.get("ADMIN_PASSWORD")
        if not raw_password:
            raw_password = "admin123"
            print(
                "⚠️  ADMIN_PASSWORD non défini dans .env — mot de passe par défaut "
                "'admin123' utilisé. Changez-le immédiatement en production !"
            )
        admin = User(
            name="Admin",
            email="admin@quickfood.sn",
            password=generate_password_hash(raw_password),
            role="admin",
            is_admin=True,
            created_at=datetime.utcnow(),
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Compte admin créé : admin@quickfood.sn")


# ── Point d'entrée ────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    socketio.run(app, debug=True)
