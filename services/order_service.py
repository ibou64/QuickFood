"""
Service commandes — création et gestion des commandes depuis le panier.
Intègre le calcul de frais de livraison par distance.
"""
from extensions import db
from models.order import Order
from models.order_item import OrderItem
from services.cart_service import CartService
from utils.delivery import calculate_delivery_fee, DEFAULT_FEE


class OrderService:

    @staticmethod
    def create_from_cart(session, user_id: int, delivery_name: str,
                         delivery_phone: str, delivery_address: str,
                         delivery_latitude=None, delivery_longitude=None,
                         promo_code: str = None) -> Order:
        """Crée une commande à partir du panier en session."""
        cart = CartService.get_cart(session)
        if not cart:
            raise ValueError("Le panier est vide.")

        restaurant_id = list(cart.values())[0].get("restaurant_id")
        if not restaurant_id:
            raise ValueError("Restaurant introuvable dans le panier.")

        # Calcul frais de livraison par distance
        from models.restaurant import Restaurant
        restaurant = Restaurant.query.get(restaurant_id)
        distance, delivery_fee = calculate_delivery_fee(
            restaurant, delivery_latitude, delivery_longitude
        )

        subtotal     = CartService.total(session)
        total_amount = subtotal + delivery_fee

        order = Order(
            user_id=user_id,
            restaurant_id=restaurant_id,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            delivery_distance=distance,
            total_amount=total_amount,
            status="En attente",
            delivery_name=delivery_name,
            delivery_phone=delivery_phone,
            delivery_address=delivery_address,
            delivery_latitude=delivery_latitude,
            delivery_longitude=delivery_longitude,
            payment_status="pending",
        )
        db.session.add(order)
        db.session.flush()

        for pid, item in cart.items():
            order_item = OrderItem(
                order_id=order.id,
                product_id=int(pid),
                quantity=item["quantity"],
                price=item["price"],
            )
            db.session.add(order_item)

        db.session.commit()

        # Application du code promo, si fourni et valide
        if promo_code:
            from services.promo_service import PromoService
            promo, error = PromoService.validate(promo_code, user_id, restaurant_id, subtotal)
            if promo:
                PromoService.apply(promo, order, user_id)

        CartService.clear(session)
        return order

    @staticmethod
    def update_status(order_id: int, new_status: str) -> Order:
        from services.notification_service import NotificationService
        from services.driver_service import DriverService

        order = Order.query.get_or_404(order_id)
        order.status = new_status
        db.session.commit()
        NotificationService.order_status_changed(order)

        # Dès que le commerce marque la commande "Prête", on cherche un livreur
        if new_status == "Prête" and not order.driver_id:
            DriverService.assign_to_order(order)

        return order

    @staticmethod
    def delete(order_id: int) -> None:
        order = Order.query.get_or_404(order_id)
        db.session.delete(order)
        db.session.commit()
