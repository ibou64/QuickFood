"""Service centralisé de notifications in-app + relais temps réel Socket.IO.
Prévu pour brancher plus tard un vrai provider SMS/push (ex: Firebase, Twilio)
sans changer les appelants : un seul point d'entrée, `NotificationService.send`.
"""
from extensions import db, socketio
from models.notification import Notification


class NotificationService:

    @staticmethod
    def send(user_id: int, title: str, message: str = "", type: str = "info", link: str | None = None):
        notif = Notification(user_id=user_id, title=title, message=message, type=type, link=link)
        db.session.add(notif)
        db.session.commit()

        # Poussée live vers le navigateur/app du destinataire (room = user_<id>)
        try:
            socketio.emit(
                "new_notification",
                notif.to_dict(),
                room=f"user_{user_id}",
            )
        except Exception:
            pass  # ne bloque jamais le flux métier si socket indisponible

        return notif

    @staticmethod
    def order_status_changed(order):
        NotificationService.send(
            user_id=order.user_id,
            title=f"Commande #{order.id} : {order.status}",
            message=f"Votre commande chez {order.restaurant.name} est maintenant « {order.status} ».",
            type="order_status",
            link=f"/client/orders",
        )

    @staticmethod
    def driver_assigned(order):
        NotificationService.send(
            user_id=order.user_id,
            title="Un livreur arrive 🛵",
            message=f"{order.driver.user.name} a pris en charge votre commande #{order.id}.",
            type="driver_assigned",
            link=f"/client/orders",
        )
        if order.driver and order.driver.user_id:
            NotificationService.send(
                user_id=order.driver.user_id,
                title="Nouvelle livraison assignée",
                message=f"Commande #{order.id} — {order.restaurant.name}.",
                type="driver_assigned",
                link="/driver/dashboard",
            )

    @staticmethod
    def unread_count(user_id: int) -> int:
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
