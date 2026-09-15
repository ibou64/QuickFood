"""
Service de paiement — intégration PayTech
"""
import requests
import uuid
from flask import current_app


class PayTechService:
    @staticmethod
    def create_payment(order, success_url, cancel_url, ipn_url):
        """
        Crée une demande de paiement PayTech
        """
        url = "https://paytech.sn/api/payment/request-payment"

        # Générer une référence unique
        ref_command = str(uuid.uuid4())

        payload = {
            "item_name": f"Commande QuickFood #{order.id}",
            "item_price": order.total_amount,
            "currency": "XOF",
            "ref_command": ref_command,
            "command_name": "Paiement QuickFood",
            "env": current_app.config.get("PAYTECH_ENV", "test"),

            # URLs
            "ipn_url": ipn_url,
            "success_url": success_url,
            "cancel_url": cancel_url
        }

        headers = {
            "API_KEY": current_app.config.get("PAYTECH_API_KEY"),
            "API_SECRET": current_app.config.get("PAYTECH_SECRET")
        }

        try:
            response = requests.post(url, data=payload, headers=headers)
            data = response.json()

            if data.get("success") == 1:
                return {
                    "success": True,
                    "url": data.get("redirect_url"),
                    "ref": ref_command
                }

            return {
                "success": False,
                "error": data
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }