# Task 2 — Testing Safety Net

## Test command

Run from the repository root:

```sh
python -m unittest discover -s tests -v
```

## Original baseline

4 original tests passed. Log: `evidence/original_tests_baseline.txt`.

## Expanded baseline (before any production changes)

20 tests total (4 original + 16 new): 16 passed, 4 failed.
Log: `evidence/expanded_tests_baseline.txt`.

## Four required testing categories

- **Normal:** quote line details and read-only behavior; quote/order consistency; consecutive order IDs, history, persistence, and stock deduction. These ensure basic purchasing behavior remains intact.
- **Boundary:** exactly 5,000 cents for the student discount (quote and placement), exactly 10,000 cents for free delivery, and ordering the final unit of stock. The 5,000-cent tests are expected to fail on the original code because the specification says *at least* 5,000.
- **Invalid/exceptional:** invalid customer, fulfillment, item quantities/types, insufficient stock, invalid products, malformed JSON, unknown order IDs, multi-line combined-stock overflow, and ensuring unsuccessful placements do not change previous saved data or use up an order number.
- **Behavior to preserve:** order cancellation restores stock, keeps historical order totals, cannot reuse cancelled order IDs, and must not restore stock a second time on repeated cancellation.

## Baseline failures and diagnosis

1. `test_student_discount_applies_at_exactly_5000_cents`: got 0 cents, expected 500. `OrderService.quote` tests `subtotal > 5000` rather than `>= 5000`.
2. `test_student_discount_applies_to_order_at_exactly_5000_cents`: got 0 cents, expected 500. Same threshold issue in `OrderService.place_order`.
3. `test_duplicate_product_lines_must_respect_combined_stock`: no error raised when ordering 3 + 3 bags even though only 4 are available. Per-line validation ignores aggregate demand.
4. `test_repeated_cancellation_does_not_restore_stock_twice`: mug stock increased to 9 rather than remaining at initial stock 8 after two cancellations. `cancel_order` restores items regardless of existing cancelled status.

**No application code was changed.** These are documented pre-existing behavioral defects, not tests to weaken. Keep this log as the before-refactor baseline; rerun after refactoring and after CR-01.
