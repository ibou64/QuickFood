"""
Utilitaires partagés : upload d'images, validations, décorateurs.
"""
import os
import uuid
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename


def allowed_file(filename: str) -> bool:
    """Vérifie que l'extension du fichier est autorisée."""
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "gif", "webp"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_uploaded_image(file) -> str | None:
    """
    Sauvegarde un fichier uploadé dans static/uploads.
    Retourne le nom de fichier ou None si invalide.
    """
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None

    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, filename))
    return filename


def save_uploaded_video(file) -> str | None:
    """
    Sauvegarde une vidéo uploadée dans static/uploads.
    Retourne le nom de fichier ou None si invalide.
    """
    if not file or file.filename == '':
        return None
    allowed_video = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
    ext = os.path.splitext(secure_filename(file.filename))[1].lower().lstrip('.')
    if ext not in allowed_video:
        return None
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, filename))
    return filename


def normalize_video_url(url: str) -> str | None:
    """Valide et normalise un lien vidéo externe."""
    if not url:
        return None
    url = url.strip()
    allowed = ('youtube.com', 'youtu.be', 'tiktok.com', 'vimeo.com',
               'dailymotion.com', 'facebook.com', 'instagram.com')
    if any(domain in url for domain in allowed):
        return url
    if url.startswith(('http://', 'https://')):
        return url
    return None


def admin_required(f):
    """Décorateur : accès réservé aux admins."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Accès refusé : vous n'êtes pas administrateur.", "danger")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated


def partner_required(f):
    """Décorateur : accès réservé aux partenaires."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "partner":
            flash("Accès réservé aux partenaires.", "danger")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated


def client_required(f):
    """Décorateur : accès réservé aux clients."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "client":
            flash("Accès réservé aux clients.", "danger")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated
