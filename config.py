import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

DB_PATH = os.path.join(INSTANCE_DIR, "quickfood.db")


def _make_sqlite_uri(path: str) -> str:
    path = path.replace("\\", "/")
    return "sqlite:///" + path


class Config:
    # =========================
    # 🔐 SECURITY
    # =========================
    # ⚠️ En production, définissez SECRET_KEY et JWT_SECRET_KEY dans .env — sinon
    # une valeur aléatoire est générée à chaque démarrage (sessions invalidées au redémarrage).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=6)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # =========================
    # 🗄 DATABASE
    # =========================
    _raw_db_url = os.environ.get("DATABASE_URL", _make_sqlite_uri(DB_PATH))
    # Render (et Heroku) fournissent "postgres://", mais SQLAlchemy 2.x exige "postgresql://"
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================
    # 📁 UPLOADS
    # =========================
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # =========================
    # 💳 PAYTECH (Wave, Orange Money, Visa)
    # =========================
    PAYTECH_API_KEY  = os.environ.get("PAYTECH_API_KEY",    "")
    PAYTECH_SECRET   = os.environ.get("PAYTECH_API_SECRET", "")
    PAYTECH_ENV      = os.environ.get("PAYTECH_ENV",        "test")  # "prod" en production
    PAYTECH_IPN_URL  = os.environ.get("PAYTECH_IPN_URL",    "")
    PAYTECH_SUCCESS_URL = os.environ.get("PAYTECH_SUCCESS_URL", "")
    PAYTECH_CANCEL_URL  = os.environ.get("PAYTECH_CANCEL_URL",  "")

    # =========================
    # 🍪 SESSION / LOGIN
    # =========================
    SESSION_COOKIE_SECURE    = bool(os.environ.get("RENDER"))
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    # =========================
    # ⚡ PERFORMANCE
    # =========================
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError(
                "SECRET_KEY manquant : définissez-le dans .env avant de lancer en production."
            )
