"""
utils/security.py — Sécurité renforcée QuickFood
- Protection brute-force (rate limiting login)
- Headers de sécurité HTTP
- Validation et sanitisation des inputs
- Token CSRF manuel léger
"""
import re
import time
import hashlib
import secrets
from collections import defaultdict
from functools import wraps
from flask import request, session, abort, current_app
from flask_login import current_user


# ── Rate limiting login (brute-force) ─────────────────────
_login_attempts = defaultdict(list)   # ip -> [timestamps]
MAX_ATTEMPTS    = 5
WINDOW_SECONDS  = 300   # 5 minutes
LOCKOUT_SECONDS = 900   # 15 minutes


def check_login_rate_limit(ip: str) -> tuple[bool, int]:
    """
    Vérifie si l'IP a dépassé la limite de tentatives de connexion.
    Retourne (autorisé, secondes_restantes).
    """
    now = time.time()
    attempts = _login_attempts[ip]

    # Nettoyer les tentatives expirées
    _login_attempts[ip] = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    attempts = _login_attempts[ip]

    if len(attempts) >= MAX_ATTEMPTS:
        oldest = min(attempts)
        remaining = int(LOCKOUT_SECONDS - (now - oldest))
        if remaining > 0:
            return False, remaining

    return True, 0


def record_login_attempt(ip: str):
    """Enregistre une tentative de connexion échouée."""
    _login_attempts[ip].append(time.time())


def reset_login_attempts(ip: str):
    """Réinitialise les tentatives après connexion réussie."""
    _login_attempts.pop(ip, None)


# ── En-têtes de sécurité HTTP ──────────────────────────────
def apply_security_headers(response):
    """Ajoute les headers de sécurité à chaque réponse."""
    response.headers['X-Content-Type-Options']    = 'nosniff'
    response.headers['X-Frame-Options']           = 'SAMEORIGIN'
    response.headers['X-XSS-Protection']          = '1; mode=block'
    response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']        = 'geolocation=(self), camera=(self), microphone=()'
    response.headers['Content-Security-Policy']   = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; "
        "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; "
        "img-src 'self' data: blob: nominatim.openstreetmap.org; "
        "media-src 'self' blob:; "
        "frame-src www.youtube.com www.tiktok.com player.vimeo.com; "
        "connect-src 'self' nominatim.openstreetmap.org;"
    )
    return response


# ── Sanitisation des inputs ────────────────────────────────
def sanitize_string(value: str, max_length: int = 500) -> str:
    """Nettoie une chaîne : supprime balises HTML dangereuses."""
    if not value:
        return ""
    # Supprimer balises script/style
    value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r'<style[^>]*>.*?</style>',  '', value, flags=re.DOTALL | re.IGNORECASE)
    # Supprimer toutes les balises HTML
    value = re.sub(r'<[^>]+>', '', value)
    # Supprimer caractères de contrôle
    value = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', value)
    return value.strip()[:max_length]


def validate_email(email: str) -> bool:
    """Valide le format d'un email."""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email or ''))


def validate_phone(phone: str) -> bool:
    """Valide un numéro de téléphone sénégalais."""
    cleaned = re.sub(r'[\s\-\.]', '', phone or '')
    return bool(re.match(r'^(\+221|00221)?[0-9]{9}$', cleaned))


# ── Token de session sécurisé ──────────────────────────────
def generate_csrf_token() -> str:
    """Génère un token CSRF et le stocke en session."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf_token(token: str) -> bool:
    """Valide le token CSRF soumis."""
    stored = session.get('_csrf_token', '')
    return stored and secrets.compare_digest(stored, token or '')


def csrf_protect(f):
    """Décorateur : vérifie le token CSRF sur les requêtes POST."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'POST':
            token = (request.form.get('_csrf_token') or
                     request.headers.get('X-CSRF-Token', ''))
            if not validate_csrf_token(token):
                abort(403)
        return f(*args, **kwargs)
    return decorated
