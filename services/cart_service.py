"""
Service panier — logique centralisée pour manipuler le panier en session.
Utilise la clé "quantity" de façon cohérente partout.
"""


class CartService:

    @staticmethod
    def get_cart(session) -> dict:
        return session.get("cart", {})

    @staticmethod
    def add(session, product) -> dict:
        cart = session.get("cart", {})
        pid = str(product.id)

        if pid in cart:
            cart[pid]["quantity"] += 1
        else:
            cart[pid] = {
                "name": product.name,
                "price": product.price,
                "quantity": 1,
                "image": product.image or "",
                "restaurant_id": product.restaurant_id,
            }

        session["cart"] = cart
        session.modified = True
        return cart

    @staticmethod
    def remove(session, product_id: int) -> dict:
        cart = session.get("cart", {})
        cart.pop(str(product_id), None)
        session["cart"] = cart
        session.modified = True
        return cart

    @staticmethod
    def update_quantity(session, product_id: int, quantity: int) -> dict:
        cart = session.get("cart", {})
        pid = str(product_id)
        if pid in cart:
            if quantity <= 0:
                del cart[pid]
            else:
                cart[pid]["quantity"] = quantity
        session["cart"] = cart
        session.modified = True
        return cart

    @staticmethod
    def increase(session, product_id: int) -> dict:
        cart = session.get("cart", {})
        pid = str(product_id)
        if pid in cart:
            cart[pid]["quantity"] += 1
        session["cart"] = cart
        session.modified = True
        return cart

    @staticmethod
    def decrease(session, product_id: int) -> dict:
        cart = session.get("cart", {})
        pid = str(product_id)
        if pid in cart:
            if cart[pid]["quantity"] > 1:
                cart[pid]["quantity"] -= 1
            else:
                del cart[pid]
        session["cart"] = cart
        session.modified = True
        return cart

    @staticmethod
    def clear(session) -> None:
        session.pop("cart", None)
        session.modified = True

    @staticmethod
    def total(session) -> float:
        cart = session.get("cart", {})
        return sum(item["price"] * item["quantity"] for item in cart.values())

    @staticmethod
    def count(session) -> int:
        cart = session.get("cart", {})
        return sum(item["quantity"] for item in cart.values())
