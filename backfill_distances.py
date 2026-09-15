"""
backfill_distances.py — Recalcule delivery_distance pour les commandes existantes.
À lancer une seule fois après seed_coords.py
"""
from app import create_app
app = create_app()

with app.app_context():
    from extensions import db
    from models.order import Order
    from utils.delivery import haversine

    orders = Order.query.filter(Order.delivery_distance == None).all()
    print(f"Commandes sans distance : {len(orders)}")

    updated = 0
    for o in orders:
        if (o.delivery_latitude and o.delivery_longitude
                and o.restaurant
                and o.restaurant.latitude and o.restaurant.longitude):
            d = haversine(
                o.restaurant.latitude, o.restaurant.longitude,
                o.delivery_latitude,   o.delivery_longitude
            )
            o.delivery_distance = round(d, 2)
            updated += 1

    db.session.commit()
    print(f"✅ {updated} distances recalculées")
    print(f"   Restantes sans GPS : {len(orders) - updated}")
