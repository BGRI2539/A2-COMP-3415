# Task 4 — Refactoring evidence

Original expanded baseline: 20 tests; 16 pass, 4 fail.
After three focused refactorings: 20 tests; 16 pass, 4 fail.
After separate behavioral defect corrections: 20 tests; 20 pass, 0 fail.

## Refactoring A — Remove duplicated validation and pricing
Before: `quote()` and `place_order()` implemented separate loops and price calculations.
After: `_build_quote(state, customer_type, items, fulfillment)` is shared by both methods. `place_order()` loads state once and uses that same state for validation and stock changes.
Reason: A pricing rule or validation change now has one implementation point.
Verification: `test_quote_and_order_have_identical_price_and_item_details` passes before and after refactoring.

## Refactoring B — Extract stock adjustment
Before: order placement and cancellation each contained nested loops to find each product and modify stock.
After: `_adjust_stock(state, lines, multiplier)` centralizes the update, using -1 on purchase and +1 on cancellation.
Reason: Smaller coordinating methods are easier to follow and stock updates use the same matching logic.
Verification: `test_cancellation_restores_stock_but_keeps_order_in_history`, `test_last_unit_in_stock_can_be_ordered`, and `test_cancelled_order_id_is_not_reused` all pass before and after.

## Refactoring C — Name business-rule constants
Before: direct literals 99, 5000, 10, 50, 100, 10000, and 600 were embedded in calculations and validation.
After: module-level named constants express these values.
Reason: Readers can identify units and business meaning without reverse-engineering the arithmetic.
Verification: All twenty tests retain the same results as the original baseline after refactoring.

## Defects corrected separately (not presented as refactoring)
1. `>=` at student discount threshold of 5000 cents.
2. Aggregate duplicate-line demand during validation before placing an order.
3. Return immediately when cancelling an already-cancelled order, without updating storage.
Each correction is covered by existing Task 2 tests and appears after the refactoring commit in local Git history.

Run tests: `python -m unittest discover -s tests -v`.
Logs: `evidence/expanded_tests_baseline.txt`, `evidence/after_refactoring.txt`, `evidence/after_defect_corrections.txt`.
