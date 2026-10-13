# Step 1: Database Setup — `database/db.py`

---

## 1. Overview

This step replaces the stub functions in `database/db.py` with a working SQLite implementation. It is the foundational step of the Spendly application because every other feature — authentication, user profiles, and expense tracking — depends on an initialized, schema-correct database being available before any route is served.

Without this step, no other step can proceed: login and registration require the `users` table, and all expense operations require both the `users` and `expenses` tables with referential integrity enforced.

---

## 2. Depends On

This is Step 1. There are no prerequisites. It does not depend on any other step in this project.

---

## 3. Routes

No new routes are introduced in this step.

All existing placeholder routes in `app.py` remain unchanged. The only modifications to `app.py` are the import of database functions and the startup initialization calls.

---

## 4. Database Schema

### Table A: `users`

| Column | SQLite Type | Constraints |
|---|---|---|
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT |
| `name` | `TEXT` | NOT NULL |
| `email` | `TEXT` | NOT NULL, UNIQUE |
| `password_hash` | `TEXT` | NOT NULL |
| `created_at` | `TEXT` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` |

### Table B: `expenses`

| Column | SQLite Type | Constraints |
|---|---|---|
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT |
| `user_id` | `INTEGER` | NOT NULL, FOREIGN KEY → `users(id)` |
| `amount` | `REAL` | NOT NULL |
| `category` | `TEXT` | NOT NULL |
| `date` | `TEXT` | NOT NULL — must be stored in `YYYY-MM-DD` format |
| `description` | `TEXT` | (none) |
| `created_at` | `TEXT` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` |

> `expenses.date` stores date values as `TEXT` in ISO 8601 format: `YYYY-MM-DD`. No other format is valid.

---

## 5. Functions to Implement (`database/db.py`)

### `get_db()`

- Opens `spendly.db` located in the project root directory.
- Sets `connection.row_factory = sqlite3.Row` so rows are accessible by column name.
- Executes `PRAGMA foreign_keys = ON` on the connection before returning it.
- Returns the open `sqlite3.Connection` object.

### `init_db()`

- Creates both the `users` table and the `expenses` table using `CREATE TABLE IF NOT EXISTS`.
- Safe to call multiple times — it must not fail or alter data if the tables already exist.
- Uses `get_db()` internally to obtain the connection.
- Commits after creating tables.

### `seed_db()`

- Checks whether the `users` table already contains any rows.
- If the table has one or more rows, returns immediately without inserting anything (idempotent guard).
- If the table is empty, inserts:
  - One demo user: `name = "Demo User"`, `email = "demo@spendly.com"`, `password` hashed from the plain-text string `"demo123"` using `werkzeug.security.generate_password_hash`.
  - Eight sample expenses linked to that demo user's `id`, covering all 7 categories (Food, Transport, Bills, Health, Entertainment, Shopping, Other — with at least one category repeated to reach 8 rows), with `date` values spread across the current calendar month in `YYYY-MM-DD` format.
- Commits after all inserts.

---

## 6. Changes to `app.py`

- Import `get_db`, `init_db`, and `seed_db` from `database.db`.
- Inside an `app.app_context()` block executed at startup (before the development server starts), call `init_db()` followed by `seed_db()` in that order.
- The database must be fully initialized and seeded before any route is served.

---

## 7. Files to Change

- `database/db.py` — replace stub function bodies with full implementation.
- `app.py` — add imports and startup initialization block.

---

## 8. Files to Create

None. No new files are introduced in this step.

---

## 9. Dependencies

No new pip packages are required.

| Library | Source | Usage |
|---|---|---|
| `sqlite3` | Python standard library | All database operations |
| `werkzeug.security` | Already in `requirements.txt` | `generate_password_hash` for seeding demo user |

---

## 10. Categories (Fixed List)

The following are the only valid expense category values used by the application:

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

---

## 11. Rules for Implementation

- No ORM. No SQLAlchemy. Use `sqlite3` from the standard library exclusively.
- All SQL statements must use parameterized queries (i.e., `?` placeholders). String formatting or f-strings must never be used to construct SQL.
- `PRAGMA foreign_keys = ON` must be executed on every connection opened by `get_db()`.
- The `amount` column must be stored as `REAL`, not `INTEGER`.
- Passwords must be hashed using `generate_password_hash` from `werkzeug.security` before being stored. Plain-text passwords must never be written to the database.
- `seed_db()` must be idempotent: calling it multiple times must produce the same database state as calling it once.
- All date values must be stored and handled as `YYYY-MM-DD` strings.

---

## 12. Expected Behavior

### `get_db()`
Returns an open `sqlite3.Connection` with `row_factory = sqlite3.Row` set and foreign key enforcement active. Every call returns a fresh connection to `spendly.db` in the project root.

### `init_db()`
Creates the `users` and `expenses` tables if they do not exist. When called on an already-initialized database, it completes without error and leaves existing data intact.

### `seed_db()`
On first call (empty `users` table): inserts one demo user and eight sample expenses, then commits. On subsequent calls: detects existing rows and returns immediately, leaving the database unchanged.

### Database-level constraints enforced
- `users.email` uniqueness is enforced by a UNIQUE constraint — duplicate emails are rejected at the database level.
- `expenses.user_id` referential integrity is enforced by a FOREIGN KEY constraint — expenses cannot reference a non-existent user.
- `NOT NULL` constraints prevent incomplete records from being inserted for required fields.

---

## 13. Error Handling Expectations

| Scenario | Expected Behavior |
|---|---|
| Insert into `users` with a duplicate `email` | SQLite raises `IntegrityError` due to UNIQUE constraint violation |
| Insert into `expenses` with a `user_id` that does not exist in `users` | SQLite raises `IntegrityError` due to FOREIGN KEY constraint violation (requires `PRAGMA foreign_keys = ON`) |
| Malformed or invalid SQL queries | Exception propagates unmodified; no silent swallowing of errors |

Errors must not be silently caught and discarded. Exceptions should surface to the caller so they are visible during development and debugging.

---

## 14. Definition of Done

- [ ] Database file `spendly.db` is created in the project root on app startup
- [ ] Both `users` and `expenses` tables exist with correct column names, types, and constraints
- [ ] Demo user (`demo@spendly.com`) exists with a werkzeug-hashed password (not plain text)
- [ ] 8 sample expense rows exist, covering all 7 categories
- [ ] Running the app multiple times does not duplicate seed data
- [ ] `flask run` (or `python app.py`) starts without errors
- [ ] Foreign key enforcement is active — inserting an expense with an invalid `user_id` fails
- [ ] All SQL in `database/db.py` uses parameterized queries with `?` placeholders
