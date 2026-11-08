"""Operations used by the command-line order desk."""

from supplydesk.storage import JsonStore


MAX_ORDER_QUANTITY = 99
STUDENT_DISCOUNT_THRESHOLD_CENTS = 5000
STUDENT_DISCOUNT_PERCENT = 10
PERCENT_DENOMINATOR = 100
HALF_CENT_ROUNDING_OFFSET = 50
FREE_DELIVERY_THRESHOLD_CENTS = 10000
DELIVERY_FEE_CENTS = 600


class OrderService:
    def __init__(self, state_path=".supplydesk/state.json"):
        self.store = JsonStore(state_path)

    def catalog(self):
        return self.store.load()["catalog"]

    def _build_quote(self, state, customer_type, items, fulfillment):
        """Validate a request and calculate its quote using the supplied snapshot."""
        if customer_type not in ("regular", "student"):
            raise ValueError("Customer type must be regular or student.")
        if fulfillment not in ("pickup", "delivery"):
            raise ValueError("Fulfillment must be pickup or delivery.")
        if not isinstance(items, list) or not items:
            raise ValueError("An order must contain at least one item.")

        lines = []
        requested_quantities = {}
        subtotal = 0
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each item must contain a product_id and quantity.")
            product = None
            for candidate in state["catalog"]:
                if candidate["product_id"] == item.get("product_id"):
                    product = candidate
                    break
            if product is None:
                raise ValueError("Unknown product.")
            quantity = item.get("quantity")
            if type(quantity) is not int or quantity < 1 or quantity > MAX_ORDER_QUANTITY:
                raise ValueError("Quantity must be an integer from 1 to 99.")
            # Check total demand across duplicate lines, not just each line.
            product_id = product["product_id"]
            requested_quantities[product_id] = (
                requested_quantities.get(product_id, 0) + quantity
            )
            if requested_quantities[product_id] > product["stock"]:
                raise ValueError("Not enough stock for " + product_id + ".")
            line_total = product["unit_price_cents"] * quantity
            subtotal += line_total
            lines.append({
                "product_id": product["product_id"],
                "name": product["name"],
                "unit_price_cents": product["unit_price_cents"],
                "quantity": quantity,
                "line_total_cents": line_total,
            })

        discount = 0
        if customer_type == "student" and subtotal >= STUDENT_DISCOUNT_THRESHOLD_CENTS:
            discount = (
                subtotal * STUDENT_DISCOUNT_PERCENT + HALF_CENT_ROUNDING_OFFSET
            ) // PERCENT_DENOMINATOR
        delivery = 0
        if (fulfillment == "delivery"
                and subtotal - discount < FREE_DELIVERY_THRESHOLD_CENTS):
            delivery = DELIVERY_FEE_CENTS
        return {
            "customer_type": customer_type,
            "fulfillment": fulfillment,
            "items": lines,
            "subtotal_cents": subtotal,
            "discount_cents": discount,
            "delivery_cents": delivery,
            "total_cents": subtotal - discount + delivery,
        }

    @staticmethod
    def _adjust_stock(state, lines, multiplier):
        """Apply item quantities to stock (+1 to restore, -1 to consume)."""
        for line in lines:
            for product in state["catalog"]:
                if product["product_id"] == line["product_id"]:
                    product["stock"] += multiplier * line["quantity"]

    def quote(self, customer_type, items, fulfillment="pickup"):
        state = self.store.load()
        return self._build_quote(state, customer_type, items, fulfillment)

    def place_order(self, customer_type, items, fulfillment="pickup"):
        state = self.store.load()
        quote = self._build_quote(state, customer_type, items, fulfillment)
        order = {
            "order_id": "ORD-" + str(state["next_order_number"]).zfill(4),
            "status": "placed",
            **quote,
        }
        self._adjust_stock(state, quote["items"], -1)
        state["next_order_number"] += 1
        state["orders"].append(order)
        self.store.save(state)
        return order

    def list_orders(self):
        return self.store.load()["orders"]

    def get_order(self, order_id):
        state = self.store.load()
        for order in state["orders"]:
            if order["order_id"] == order_id:
                return order
        raise ValueError("Unknown order: " + order_id)

    def cancel_order(self, order_id):
        state = self.store.load()
        order = None
        for candidate in state["orders"]:
            if candidate["order_id"] == order_id:
                order = candidate
                break
        if order is None:
            raise ValueError("Unknown order: " + order_id)
        if order["status"] == "cancelled":
            return order
        self._adjust_stock(state, order["items"], 1)
        order["status"] = "cancelled"
        self.store.save(state)
        return order
