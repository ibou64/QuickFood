"""
Service de calcul de frais de livraison par distance (Haversine).
Adapté au marché sénégalais — tarifs en FCFA.
"""
import math


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Retourne la distance en km entre deux points GPS."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# Zones tarifaires FCFA — adaptées au marché sénégalais
DELIVERY_TIERS = [
    (2,          500),
    (5,         1000),
    (10,        1500),
    (20,        2500),
    (float("inf"), 3500),
]

DEFAULT_FEE = 1000  # FCFA si coordonnées absentes


def calculate_delivery_fee(restaurant, delivery_lat, delivery_lng):
    """
    Retourne (distance_km, frais_fcfa).
    Si coordonnées manquantes → frais fixe par défaut.
    """
    try:
        if not all([
            restaurant.latitude, restaurant.longitude,
            delivery_lat, delivery_lng
        ]):
            return None, DEFAULT_FEE

        distance = haversine(
            restaurant.latitude, restaurant.longitude,
            float(delivery_lat), float(delivery_lng)
        )

        for limit, fee in DELIVERY_TIERS:
            if distance <= limit:
                return round(distance, 2), fee

        return round(distance, 2), 3500

    except Exception:
        return None, DEFAULT_FEE
