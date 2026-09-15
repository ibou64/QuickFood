"""
services/split_service.py
─────────────────────────────────────────────────────────────────────────────
Split Payment automatique — QuickFood x Restaurant

Logique :
  total_amount = subtotal + delivery_fee

  commission_amount = subtotal × (commission_rate / 100)
  delivery_fee      → 100 % QuickFood (frais de livraison)
  restaurant_amount = subtotal - commission_amount

  QuickFood encaisse : commission_amount + delivery_fee
  Restaurant reçoit  : restaurant_amount

Appelé depuis le webhook IPN PayTech dès que type_event == "sale_complete".
Le split est purement comptable dans un premier temps (enregistrement en DB).
Pour le virement réel vers le restaurant, voir la section "Étape suivante"
en bas de ce fichier.
"""

from datetime import datetime
from extensions import db


class SplitService:

    # ─── Calcul du split ──────────────────────────────────────────────────────
    @staticmethod
    def calculate(order) -> dict:
        """
        Calcule la répartition à partir des données de la commande.

        Returns dict :
          commission_rate   : float  — taux appliqué (ex: 10.0)
          commission_amount : float  — part QuickFood sur les articles
          delivery_fee      : float  — frais de livraison (100 % QuickFood)
          restaurant_amount : float  — part nette du restaurant
          quickfood_total   : float  — total encaissé par QuickFood
        """
        rate = float(order.restaurant.commission_rate or 10.0)

        subtotal     = float(order.subtotal or 0.0)
        delivery_fee = float(order.delivery_fee or 0.0)

        commission_amount = round(subtotal * rate / 100, 2)
        restaurant_amount = round(subtotal - commission_amount, 2)
        quickfood_total   = round(commission_amount + delivery_fee, 2)

        return {
            "commission_rate":   rate,
            "commission_amount": commission_amount,
            "delivery_fee":      delivery_fee,
            "restaurant_amount": restaurant_amount,
            "quickfood_total":   quickfood_total,
        }

    # ─── Exécution du split après confirmation du paiement ────────────────────
    @staticmethod
    def execute(order) -> bool:
        """
        Enregistre le split en base dès que le paiement est confirmé.
        Retourne True si tout s'est bien passé, False sinon.

        Appelé depuis le webhook IPN → payment.py → /payment/ipn
        """
        if order.split_status == "done":
            # Déjà traité (idempotence : PayTech peut renvoyer l'IPN plusieurs fois)
            return True

        try:
            split = SplitService.calculate(order)

            order.commission_rate   = split["commission_rate"]
            order.commission_amount = split["commission_amount"]
            order.restaurant_amount = split["restaurant_amount"]
            order.split_status      = "done"
            order.split_done_at     = datetime.utcnow()

            db.session.commit()

            SplitService._log(order, split)
            return True

        except Exception as exc:
            db.session.rollback()
            order.split_status = "error"
            try:
                db.session.commit()
            except Exception:
                pass

            import traceback
            print(f"[SplitService] ERREUR split commande #{order.id}: {exc}")
            traceback.print_exc()
            return False

    # ─── Résumé lisible (pour templates / admin) ──────────────────────────────
    @staticmethod
    def summary(order) -> dict:
        """
        Retourne un dict prêt pour l'affichage dans les templates Jinja2.
        """
        if order.split_status != "done":
            return {"ready": False}

        return {
            "ready":             True,
            "total":             order.total_amount,
            "subtotal":          order.subtotal,
            "delivery_fee":      order.delivery_fee,
            "commission_rate":   order.commission_rate,
            "commission_amount": order.commission_amount,
            "restaurant_amount": order.restaurant_amount,
            "quickfood_total":   round(
                (order.commission_amount or 0) + (order.delivery_fee or 0), 2
            ),
            "split_done_at":     order.split_done_at,
        }

    # ─── Log interne ─────────────────────────────────────────────────────────
    @staticmethod
    def _log(order, split):
        print(
            f"[SplitService] ✓ Commande #{order.id} | "
            f"Total: {order.total_amount:,.0f} XOF | "
            f"Commission QuickFood ({split['commission_rate']}%): "
            f"{split['commission_amount']:,.0f} XOF | "
            f"Livraison: {split['delivery_fee']:,.0f} XOF | "
            f"→ Restaurant: {split['restaurant_amount']:,.0f} XOF"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE SUIVANTE — Virement réel vers le restaurant
# ─────────────────────────────────────────────────────────────────────────────
# Le split ci-dessus est comptable. Pour déclencher un virement automatique
# vers le compte Wave/Orange Money du restaurant, deux options :
#
# Option A — PayTech Transfer API (recommandé pour l'écosystème Sénégal)
#   Après execute(), appeler PayTech /api/transfer/send avec :
#     amount    = split["restaurant_amount"]
#     recipient = restaurant.wave_phone (ou orange_money_phone)
#   → Ajouter wave_phone / om_phone sur le modèle Restaurant.
#
# Option B — Virement manuel périodique (le plus simple à démarrer)
#   L'admin exporte depuis /admin les montants dus par restaurant
#   et effectue les virements Wave Business en lot chaque semaine.
#   C'est ce que font la plupart des startups locales au démarrage.
#
# La colonne split_status="done" et restaurant_amount permettent dans les deux
# cas de savoir exactement ce qui est dû à chaque restaurant.
# ─────────────────────────────────────────────────────────────────────────────
