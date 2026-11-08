# Task 6 — AI interaction record (post-Checkpoint A)

This record documents three distinct AI recommendations generated in the present ChatGPT working session in response to the request to complete the post-Checkpoint A work. This is a condensed record of recommendations and their evaluation, not a verbatim transcript of every earlier chat turn. The assignment owner should additionally retain/share the conversation link or export for independent verification.

## Recommendation 1: ACCEPT
AI suggestion: "Extract the duplicate request validation and price computation from `quote()` and `place_order()` into one reusable operation."
Evaluation: The original `service.py` contains nearly identical loops and monetary calculations. Both operations must use the same rules. The shared `_build_quote()` accepts an explicitly loaded state, allowing order placement to validate the same stock snapshot it later modifies.
Evidence: `supplydesk/service.py`; `test_quote_and_order_have_identical_price_and_item_details`; baseline and post-refactoring logs show the same 16 passes and four known failures.
Action: Accepted. Implemented `_build_quote()`.

## Recommendation 2: MODIFY
AI suggestion: "Replace the unexplained numeric literals with named constants; while editing pricing, also fix the student discount threshold in the refactoring."
Evaluation: Named constants are a safe maintainability change, but changing `>` to `>=` changes observable results at exactly 5,000 cents. Combining a behavioral correction with a refactor would conceal whether the refactor preserved behavior.
Evidence: `test_student_discount_applies_at_exactly_5000_cents` and `test_student_discount_applies_to_order_at_exactly_5000_cents` fail in the original and refactored baseline, then pass after the separate correction.
Action: Modified the recommendation. Added constants during refactoring; corrected the boundary later in a separately recorded defect-fix commit.

## Recommendation 3: REJECT
AI suggestion: "Replace the application's JSON storage with SQLite as part of the refactor to improve data integrity."
Evaluation: The provided functional specification expressly defines a local JSON save-file implementation, version 1, and excludes concurrent instances and crash-recovery guarantees. A database migration is not needed to address the diagnosed smells, would add an unrequested dependency and migration work, and would exceed the assignment's focused-refactoring scope.
Evidence: `FUNCTIONAL_SPEC.md` (Saved data and scope limits); `supplydesk/storage.py`; existing persistence tests.
Action: Rejected. Kept `JsonStore` and JSON persistence unchanged.

## Technical review
The AI recommendations were not accepted without inspection. The original source was read, the original 20-test baseline was rerun, the refactoring was checked with the same suite, and the behavior changes were isolated in a later step. The incomplete instructor CR-01 was not invented or implemented.
