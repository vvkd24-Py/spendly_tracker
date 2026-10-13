# Spendly — Test Analysis Report

**Run date:** 2026-10-13  
**Python:** 3.13.9 · pytest 8.4.2 · Flask 3.1.2 · SQLite  
**Duration:** 5.75 s  
**Result: 47 / 47 passed · 0 failed · 0 skipped**

---

## Summary

| Metric | Value |
|---|---|
| Total tests | 47 |
| Passed | 47 |
| Failed | 0 |
| Skipped | 0 |
| Unit tests | 15 |
| Route tests | 32 |
| Test suites | 4 |
| Runtime | 5.75 s |

---

## Coverage by step

| Step | Topic | Suite | Tests |
|---|---|---|---|
| 01–04 | DB setup, Register, Login, Profile layout | `test_backend_connection.py` | 10 |
| 05–06 | Profile routes + date filter | `test_backend_connection.py` | (included above) |
| 07 | Add Expense | `test_add_expense.py` | 12 |
| 08 | Edit Expense | `test_edit_expense.py` | 17 |
| 09 | Delete Expense | `test_delete_expense.py` | 8 |

---

## Suite: `tests/test_backend_connection.py` — 10 / 10

Covers Steps 01–06: DB query helpers and the profile route.

| # | Test | Type | Result |
|---|---|---|---|
| 1 | `test_get_user_by_id_valid` | unit | PASS |
| 2 | `test_get_user_by_id_nonexistent` | unit | PASS |
| 3 | `test_get_summary_stats_with_expenses` | unit | PASS |
| 4 | `test_get_summary_stats_no_expenses` | unit | PASS |
| 5 | `test_get_recent_transactions_with_expenses` | unit | PASS |
| 6 | `test_get_recent_transactions_no_expenses` | unit | PASS |
| 7 | `test_get_category_breakdown_with_expenses` | unit | PASS |
| 8 | `test_get_category_breakdown_no_expenses` | unit | PASS |
| 9 | `test_profile_unauthenticated` | route | PASS |
| 10 | `test_profile_authenticated_seed_user` | route | PASS |

**What is verified:**
- `get_user_by_id` returns correct fields and `None` for unknown id
- `get_summary_stats` returns correct total (₹346.24), count (8), and top category (Bills) for seed data; returns zero-state for user with no expenses
- `get_recent_transactions` returns all 8 rows in newest-first order with correct fields; returns empty list for user with no expenses
- `get_category_breakdown` returns all 7 categories ordered by amount descending; percentage values sum exactly to 100; returns empty list for user with no expenses
- Unauthenticated GET `/profile` redirects (302) to `/login`
- Authenticated GET `/profile` returns 200 with Demo User data, ₹ symbol, seed total, Bills category, 8+ transaction rows, 7+ breakdown rows, and newest transaction before oldest in the table

---

## Suite: `tests/test_add_expense.py` — 12 / 12

Covers Step 07: `insert_expense` helper and the `POST /expenses/add` route.

| # | Test | Type | Result |
|---|---|---|---|
| 1 | `test_insert_expense_returns_id` | unit | PASS |
| 2 | `test_insert_expense_null_description` | unit | PASS |
| 3 | `test_get_add_expense_unauthenticated_redirects` | route | PASS |
| 4 | `test_get_add_expense_authenticated_ok` | route | PASS |
| 5 | `test_get_add_expense_has_all_categories` | route | PASS |
| 6 | `test_post_valid_expense_redirects_to_profile` | route | PASS |
| 7 | `test_post_zero_amount_fails` | route | PASS |
| 8 | `test_post_negative_amount_fails` | route | PASS |
| 9 | `test_post_non_numeric_amount_fails` | route | PASS |
| 10 | `test_post_invalid_category_fails` | route | PASS |
| 11 | `test_post_invalid_date_fails` | route | PASS |
| 12 | `test_post_no_description_succeeds` | route | PASS |

**What is verified:**
- `insert_expense` returns an integer id; the row is readable in the DB with correct amount, category, and description
- `insert_expense` with `description=None` stores NULL in the DB
- Unauthenticated GET `/expenses/add` redirects (302) to `/login`
- Authenticated GET `/expenses/add` returns 200 with all 7 category options
- POST with valid data redirects (302) to `/profile`
- POST with `amount=0`, negative amount, or non-numeric amount returns 200 with error message
- POST with invalid category returns 200 with error message
- POST with invalid date string returns 200 with error message
- POST with empty description redirects (302) to `/profile`; DB row has `description IS NULL`

---

## Suite: `tests/test_edit_expense.py` — 17 / 17

Covers Step 08: `get_expense_by_id`, `update_expense` helpers and the `GET/POST /expenses/<id>/edit` route.

| # | Test | Type | Result |
|---|---|---|---|
| 1 | `test_get_expense_by_id_valid` | unit | PASS |
| 2 | `test_get_expense_by_id_wrong_user` | unit | PASS |
| 3 | `test_get_expense_by_id_nonexistent` | unit | PASS |
| 4 | `test_update_expense_valid` | unit | PASS |
| 5 | `test_update_expense_wrong_user_no_change` | unit | PASS |
| 6 | `test_get_edit_unauthenticated_redirects` | route | PASS |
| 7 | `test_get_edit_own_expense_ok` | route | PASS |
| 8 | `test_get_edit_other_user_expense_404` | route | PASS |
| 9 | `test_get_edit_nonexistent_expense_404` | route | PASS |
| 10 | `test_post_edit_unauthenticated_redirects` | route | PASS |
| 11 | `test_post_edit_valid_redirects_and_updates` | route | PASS |
| 12 | `test_post_edit_other_user_expense_404` | route | PASS |
| 13 | `test_post_edit_zero_amount_fails` | route | PASS |
| 14 | `test_post_edit_non_numeric_amount_fails` | route | PASS |
| 15 | `test_post_edit_invalid_category_fails` | route | PASS |
| 16 | `test_post_edit_invalid_date_fails` | route | PASS |
| 17 | `test_post_edit_no_description_succeeds` | route | PASS |

**What is verified:**
- `get_expense_by_id` returns the correct row dict when id and user_id match
- `get_expense_by_id` returns `None` when user_id does not match (ownership check)
- `get_expense_by_id` returns `None` for a non-existent id
- `update_expense` updates all fields (amount, category, date, description) when user_id matches
- `update_expense` is a no-op (row unchanged) when user_id does not match
- Unauthenticated GET and POST both redirect (302) to `/login`
- Authenticated GET for own expense returns 200 with pre-filled form and all 7 categories
- GET for another user's expense returns 404
- GET for non-existent id returns 404
- POST with valid data redirects (302) to `/profile`; DB row reflects updated values
- POST for another user's expense returns 404
- POST with `amount=0`, non-numeric amount, invalid category, or invalid date returns 200 with error message
- POST with empty description redirects (302) to `/profile`; DB row has `description IS NULL`

---

## Suite: `tests/test_delete_expense.py` — 8 / 8

Covers Step 09: `delete_expense` helper and the `POST /expenses/<id>/delete` route.

| # | Test | Type | Result |
|---|---|---|---|
| 1 | `test_delete_expense_removes_row` | unit | PASS |
| 2 | `test_delete_expense_wrong_user_no_change` | unit | PASS |
| 3 | `test_delete_expense_nonexistent_no_error` | unit | PASS |
| 4 | `test_post_delete_unauthenticated_redirects` | route | PASS |
| 5 | `test_post_delete_own_expense_redirects_and_removes` | route | PASS |
| 6 | `test_post_delete_other_user_expense_404` | route | PASS |
| 7 | `test_post_delete_nonexistent_expense_404` | route | PASS |
| 8 | `test_get_delete_returns_405` | route | PASS |

**What is verified:**
- `delete_expense` removes the row from the DB when user_id matches
- `delete_expense` leaves the row untouched when user_id does not match (ownership guard in WHERE clause)
- `delete_expense` raises no error when the id does not exist; DB is unchanged
- Unauthenticated POST redirects (302) to `/login`
- Authenticated POST for own expense redirects (302) to `/profile`; row confirmed absent from DB
- POST for another user's expense returns 404; row confirmed still present in DB
- POST for non-existent id returns 404
- GET to the delete URL returns 405 (Method Not Allowed) — route is POST-only

---

## Test isolation strategy

Tests in `test_add_expense.py`, `test_edit_expense.py`, and `test_delete_expense.py` use per-test-function isolated SQLite databases:

1. A `NamedTemporaryFile` with `.db` suffix is created for each test
2. `unittest.mock.patch.object(db_module, "DB_PATH", tmp.name)` redirects all `get_db()` calls to the temp file during setup
3. `init_db()` and `seed_db()` are called on the temp file to create a clean 8-row starting state
4. The patch is released before `yield`, so only fixtures that explicitly patch are affected — `test_backend_connection.py` continues to use the real `spendly.db`
5. The temp file is deleted after each test

This ensures the suite is idempotent: running it multiple times never accumulates rows in `spendly.db` and never causes failures in `test_backend_connection.py`'s count/total assertions.

---

## Raw pytest output

```
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-8.4.2, pluggy-1.5.0
rootdir: C:\Users\Ishan Deep\OneDrive\Desktop\Expense_Tracker_Basic-main
plugins: anyio-4.10.0, langsmith-0.7.10
collected 47 items

tests/test_add_expense.py::test_insert_expense_returns_id PASSED         [  2%]
tests/test_add_expense.py::test_insert_expense_null_description PASSED   [  4%]
tests/test_add_expense.py::test_get_add_expense_unauthenticated_redirects PASSED [  6%]
tests/test_add_expense.py::test_get_add_expense_authenticated_ok PASSED  [  8%]
tests/test_add_expense.py::test_get_add_expense_has_all_categories PASSED [ 10%]
tests/test_add_expense.py::test_post_valid_expense_redirects_to_profile PASSED [ 12%]
tests/test_add_expense.py::test_post_zero_amount_fails PASSED            [ 14%]
tests/test_add_expense.py::test_post_negative_amount_fails PASSED        [ 17%]
tests/test_add_expense.py::test_post_non_numeric_amount_fails PASSED     [ 19%]
tests/test_add_expense.py::test_post_non_numeric_amount_fails PASSED     [ 21%]
tests/test_add_expense.py::test_post_invalid_category_fails PASSED       [ 23%]
tests/test_add_expense.py::test_post_invalid_date_fails PASSED           [ 25%]
tests/test_add_expense.py::test_post_no_description_succeeds PASSED      [ 30%]
tests/test_backend_connection.py::test_get_user_by_id_valid PASSED       [ 27%]
tests/test_backend_connection.py::test_get_user_by_id_nonexistent PASSED [ 29%]
tests/test_backend_connection.py::test_get_summary_stats_with_expenses PASSED [ 31%]
tests/test_backend_connection.py::test_get_summary_stats_no_expenses PASSED [ 34%]
tests/test_backend_connection.py::test_get_recent_transactions_with_expenses PASSED [ 36%]
tests/test_backend_connection.py::test_get_recent_transactions_no_expenses PASSED [ 38%]
tests/test_backend_connection.py::test_get_category_breakdown_with_expenses PASSED [ 40%]
tests/test_backend_connection.py::test_get_category_breakdown_no_expenses PASSED [ 42%]
tests/test_backend_connection.py::test_profile_unauthenticated PASSED    [ 44%]
tests/test_backend_connection.py::test_profile_authenticated_seed_user PASSED [ 46%]
tests/test_delete_expense.py::test_delete_expense_removes_row PASSED     [ 48%]
tests/test_delete_expense.py::test_delete_expense_wrong_user_no_change PASSED [ 51%]
tests/test_delete_expense.py::test_delete_expense_nonexistent_no_error PASSED [ 53%]
tests/test_delete_expense.py::test_post_delete_unauthenticated_redirects PASSED [ 55%]
tests/test_delete_expense.py::test_post_delete_own_expense_redirects_and_removes PASSED [ 57%]
tests/test_delete_expense.py::test_post_delete_other_user_expense_404 PASSED [ 59%]
tests/test_delete_expense.py::test_post_delete_nonexistent_expense_404 PASSED [ 61%]
tests/test_delete_expense.py::test_get_delete_returns_405 PASSED         [ 63%]
tests/test_edit_expense.py::test_get_expense_by_id_valid PASSED          [ 65%]
tests/test_edit_expense.py::test_get_expense_by_id_wrong_user PASSED     [ 68%]
tests/test_edit_expense.py::test_get_expense_by_id_nonexistent PASSED    [ 70%]
tests/test_edit_expense.py::test_update_expense_valid PASSED             [ 72%]
tests/test_edit_expense.py::test_update_expense_wrong_user_no_change PASSED [ 74%]
tests/test_edit_expense.py::test_get_edit_unauthenticated_redirects PASSED [ 76%]
tests/test_edit_expense.py::test_get_edit_own_expense_ok PASSED          [ 78%]
tests/test_edit_expense.py::test_get_edit_other_user_expense_404 PASSED  [ 80%]
tests/test_edit_expense.py::test_get_edit_nonexistent_expense_404 PASSED [ 82%]
tests/test_edit_expense.py::test_post_edit_unauthenticated_redirects PASSED [ 85%]
tests/test_edit_expense.py::test_post_edit_valid_redirects_and_updates PASSED [ 87%]
tests/test_edit_expense.py::test_post_edit_other_user_expense_404 PASSED [ 89%]
tests/test_edit_expense.py::test_post_edit_zero_amount_fails PASSED      [ 91%]
tests/test_edit_expense.py::test_post_edit_non_numeric_amount_fails PASSED [ 93%]
tests/test_edit_expense.py::test_post_edit_invalid_category_fails PASSED [ 95%]
tests/test_edit_expense.py::test_post_edit_invalid_date_fails PASSED     [ 97%]
tests/test_edit_expense.py::test_post_edit_no_description_succeeds PASSED [100%]

============================= 47 passed in 5.75s ==============================
```
