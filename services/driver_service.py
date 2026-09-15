"""Attribution automatique de livreur + suivi de position."""
from datetime import datetime
from extensions import db
from models.driver import Driver
from utils.delivery import haversine


class DriverService:

    @staticmethod
    def find_nearest_available(restaurant_lat, restaurant_lng, max_radius_km: float = 15.0):
        """Retourne le livreur disponible le plus proche du restaurant, ou None."""
        candidates = Driver.query.filter_by(is_active=True, is_available=True).all()
        best, best_dist = None, None

        for d in candidates:
            if d.current_lat is None or d.current_lng is None:
                continue
            if restaurant_lat is None or restaurant_lng is None:
                continue
            dist = haversine(restaurant_lat, restaurant_lng, d.current_lat, d.current_lng)
            if dist <= max_radius_km and (best_dist is None or dist < best_dist):
                best, best_dist = d, dist

        return best

    @staticmethod
    def assign_to_order(order):
        """Assigne automatiquement le livreur le plus proche à une commande. Retourne True/False."""
        from services.notification_service import NotificationService

        restaurant = order.restaurant
        driver = DriverService.find_nearest_available(restaurant.latitude, restaurant.longitude)
        if not driver:
            return False

        order.driver_id = driver.id
        order.driver_assigned_at = datetime.utcnow()
        order.status = "Livreur assigné"
        driver.is_available = False  # occupé le temps de la course
        db.session.commit()

        NotificationService.driver_assigned(order)
        return True

    @staticmethod
    def update_location(driver: Driver, lat: float, lng: float):
        driver.current_lat = lat
        driver.current_lng = lng
        driver.last_seen_at = datetime.utcnow()
        db.session.commit()

        # Diffuse la position en direct à tous ceux qui suivent une commande de ce livreur
        from extensions import socketio
        socketio.emit(
            "driver_location",
            {"driver_id": driver.id, "lat": lat, "lng": lng},
            room=f"driver_{driver.id}_watchers",
        )

    @staticmethod
    def complete_delivery(order):
        driver = order.driver
        order.status = "Livrée"
        order.delivered_at = datetime.utcnow()
        if driver:
            driver.is_available = True
            driver.total_deliveries = (driver.total_deliveries or 0) + 1
        db.session.commit()

        from services.notification_service import NotificationService
        NotificationService.order_status_changed(order)
