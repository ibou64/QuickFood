"""Validation et application des codes promo."""
from datetime import datetime
from extensions import db
from models.promo import PromoCode, PromoRedemption


class PromoService:

    @staticmethod
    def validate(code: str, user_id: int, restaurant_id: int, subtotal: float):
        """Retourne (promo, erreur). `promo` est None si invalide."""
        if not code:
            return None, "Code promo requis."

        promo = PromoCode.query.filter(db.func.upper(PromoCode.code) == code.strip().upper()).first()
        if not promo:
            return None, "Code promo introuvable."
        if not promo.is_valid_now():
            return None, "Ce code promo n'est plus valide."
        if promo.restaurant_id and promo.restaurant_id != restaurant_id:
            return None, "Ce code n'est pas valable pour ce commerce."
        if subtotal < (promo.min_order_amount or 0):
            return None, f"Commande minimum de {promo.min_order_amount:.0f} FCFA requise pour ce code."

        uses_by_user = PromoRedemption.query.filter_by(promo_id=promo.id, user_id=user_id).count()
        if uses_by_user >= (promo.max_uses_per_user or 1):
            return None, "Vous avez déjà utilisé ce code promo."

        return promo, None

    @staticmethod
    def apply(promo: PromoCode, order, user_id: int):
        discount = promo.compute_discount(order.subtotal)
        order.promo_code_id = promo.id
        order.discount_amount = discount
        order.total_amount = max(0, order.subtotal + order.delivery_fee - discount)

        promo.used_count = (promo.used_count or 0) + 1
        db.session.add(PromoRedemption(
            promo_id=promo.id, user_id=user_id, order_id=order.id, discount_amount=discount,
        ))
        db.session.commit()
        return discount
