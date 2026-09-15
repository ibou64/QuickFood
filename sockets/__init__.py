"""Événements Socket.IO — notifications live + suivi de livraison en temps réel."""
from flask_socketio import join_room, leave_room, emit
from extensions import socketio


@socketio.on("join_user_room")
def on_join_user_room(data):
    """Le client rejoint sa room personnelle pour recevoir ses notifications live."""
    user_id = data.get("user_id") if isinstance(data, dict) else None
    if user_id:
        join_room(f"user_{user_id}")


@socketio.on("watch_driver")
def on_watch_driver(data):
    """Un client (page de suivi de commande) s'abonne à la position d'un livreur."""
    driver_id = data.get("driver_id") if isinstance(data, dict) else None
    if driver_id:
        join_room(f"driver_{driver_id}_watchers")


@socketio.on("unwatch_driver")
def on_unwatch_driver(data):
    driver_id = data.get("driver_id") if isinstance(data, dict) else None
    if driver_id:
        leave_room(f"driver_{driver_id}_watchers")
