"""Cloche de notifications in-app (liste, marquer comme lu)."""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from extensions import db
from models.notification import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/")
@login_required
def list_notifications():
    notifs = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc()).limit(30).all()
    )
    return jsonify({
        "unread_count": Notification.query.filter_by(user_id=current_user.id, is_read=False).count(),
        "items": [n.to_dict() for n in notifs],
    })


@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        return jsonify({"error": "Non autorisé"}), 403
    notif.is_read = True
    db.session.commit()
    return jsonify({"ok": True})


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})
