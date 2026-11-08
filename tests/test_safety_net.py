"""Specification-based regression tests for the original Campus Supply Desk.

These tests deliberately document existing defects; they do not alter production code.
"""

from pathlib import Path
import tempfile
import unittest

from supplydesk.service import OrderService


class SafetyNetTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "state.json"
        self.service = OrderService(self.path)

    @staticmethod
    def item(product_id, quantity):
        return {"product_id": product_id, "quantity": quantity}

    @staticmethod
    def stock(catalog, product_id):
        return next(product["stock"] for product in catalog
                    if product["product_id"] == product_id)

    # Normal behavior
    def test_quote_contains_correct_item_details_and_does_not_write_state(self):
        quote = self.service.quote("regular", [self.item("notebook", 2)])
        self.assertEqual(quote["items"], [{
            "product_id": "notebook", "name": "Notebook",
            "unit_price_cents": 500, "quantity": 2, "line_total_cents": 1000,
        }])
        self.assertEqual(quote["total_cents"], 1000)
        self.assertFalse(self.path.exists(), "Quotes must not create save files")

    def test_quote_and_order_have_identical_price_and_item_details(self):
        items = [self.item("hoodie", 2)]
        quote = self.service.quote("student", items, "delivery")
        order = self.service.place_order("student", items, "delivery")
        for key in ("customer_type", "fulfillment", "items", "subtotal_cents",
                    "discount_cents", "delivery_cents", "total_cents"):
            self.assertEqual(quote[key], order[key], key)
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(self.stock(self.service.catalog(), "hoodie"), 3)

    def test_history_and_order_ids_survive_reopening(self):
        first = self.service.place_order("regular", [self.item("mug", 1)])
        second = self.service.place_order("student", [self.item("notebook", 1)])
        reopened = OrderService(self.path)
        self.assertEqual([o["order_id"] for o in reopened.list_orders()],
                         ["ORD-0001", "ORD-0002"])
        self.assertEqual(reopened.get_order(first["order_id"]), first)
        self.assertEqual(reopened.get_order(second["order_id"]), second)
        self.assertEqual(self.stock(reopened.catalog(), "mug"), 7)

    # Boundary behavior
    def test_student_discount_applies_at_exactly_5000_cents(self):
        items = [self.item("bag", 2)]
        quote = self.service.quote("student", items)
        self.assertEqual(quote["subtotal_cents"], 5000)
        self.assertEqual(quote["discount_cents"], 500)
        self.assertEqual(quote["total_cents"], 4500)

    def test_student_discount_applies_to_order_at_exactly_5000_cents(self):
        order = self.service.place_order("student", [self.item("bag", 2)])
        self.assertEqual(order["discount_cents"], 500)
        self.assertEqual(order["total_cents"], 4500)

    def test_delivery_is_free_at_exactly_10000_cents(self):
        quote = self.service.quote("regular", [self.item("bag", 4)], "delivery")
        self.assertEqual(quote["subtotal_cents"], 10000)
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 10000)

    def test_last_unit_in_stock_can_be_ordered(self):
        order = self.service.place_order("regular", [self.item("bag", 4)])
        self.assertEqual(order["status"], "placed")
        self.assertEqual(self.stock(self.service.catalog(), "bag"), 0)

    # Invalid or exceptional behavior
    def test_invalid_customer_fulfillment_and_items_are_rejected(self):
        for customer, items, fulfillment in (
            ("guest", [self.item("notebook", 1)], "pickup"),
            ("regular", [self.item("notebook", 1)], "shipping"),
            ("regular", [], "pickup"),
            ("regular", [self.item("unknown", 1)], "pickup"),
            ("regular", [self.item("notebook", 21)], "pickup"),
        ):
            with self.subTest(customer=customer, items=items, fulfillment=fulfillment):
                with self.assertRaises(ValueError):
                    self.service.place_order(customer, items, fulfillment)
                self.assertFalse(self.path.exists())

    def test_invalid_quantity_types_and_limits_are_rejected(self):
        for quantity in (0, -1, 100, True, 1.5, "2", None):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    self.service.quote("regular", [self.item("notebook", quantity)])
                self.assertFalse(self.path.exists())

    def test_failed_placement_does_not_change_prior_order_or_stock(self):
        first = self.service.place_order("regular", [self.item("mug", 1)])
        state_before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.service.place_order("regular", [
                self.item("notebook", 2), self.item("hoodie", 6)
            ])
        self.assertEqual(self.path.read_bytes(), state_before)
        self.assertEqual(self.service.get_order(first["order_id"]), first)
        second = self.service.place_order("regular", [self.item("mug", 1)])
        self.assertEqual(second["order_id"], "ORD-0002")

    def test_duplicate_product_lines_must_respect_combined_stock(self):
        # Each line individually fits, but combined demand (6) exceeds stock (4).
        items = [self.item("bag", 3), self.item("bag", 3)]
        with self.assertRaises(ValueError):
            self.service.place_order("regular", items)
        self.assertFalse(self.path.exists())

    def test_corrupt_save_file_raises_error_without_resetting_data(self):
        self.path.write_text("{invalid json", encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.service.catalog()
        self.assertEqual(self.path.read_bytes(), before)

    def test_unknown_order_rejected_without_mutation(self):
        self.service.place_order("regular", [self.item("notebook", 1)])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.service.cancel_order("ORD-9999")
        self.assertEqual(self.path.read_bytes(), before)

    # Behavior to preserve across refactoring
    def test_cancellation_restores_stock_but_keeps_order_in_history(self):
        order = self.service.place_order("regular", [self.item("notebook", 2)])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["total_cents"], order["total_cents"])
        self.assertEqual(self.stock(self.service.catalog(), "notebook"), 20)
        self.assertEqual([o["status"] for o in self.service.list_orders()], ["cancelled"])

    def test_repeated_cancellation_does_not_restore_stock_twice(self):
        order = self.service.place_order("regular", [self.item("mug", 1)])
        self.service.cancel_order(order["order_id"])
        catalog_before = self.service.catalog()
        self.service.cancel_order(order["order_id"])
        self.assertEqual(self.service.catalog(), catalog_before)
        self.assertEqual(self.stock(self.service.catalog(), "mug"), 8)

    def test_cancelled_order_id_is_not_reused(self):
        order = self.service.place_order("regular", [self.item("mug", 1)])
        self.service.cancel_order(order["order_id"])
        next_order = self.service.place_order("regular", [self.item("mug", 1)])
        self.assertEqual(next_order["order_id"], "ORD-0002")
        self.assertEqual(len(self.service.list_orders()), 2)


if __name__ == "__main__":
    unittest.main()
