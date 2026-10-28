---
description: Full quality analysis of Spendly — runs the test suite, maps route and query-function coverage, checks for code and CSS quality issues, and delivers a prioritized action plan.
allowed-tools: Bash(pytest tests/ -v --tb=short), Bash(python -m pytest tests/ -v --tb=short)
---

# Spendly Quality Analysis

Run a complete quality analysis of the Spendly Flask application across four areas:
test suite health, route coverage, query-function coverage, and static code quality.

Present a single structured report, then offer to implement items from the action plan.

---

## Pre-flight

Read `app.py` and `database/queries.py` before running anything. You need the full
list of routes and query functions before you can assess coverage. Do not skip this.

---

## Phase 1 — Run the Test Suite

Run:

```
pytest tests/ -v --tb=short
```

Capture:
- Total collected, passed, failed, errored
- Names and short tracebacks of any failing tests
- Total duration

If pytest exits with a collection error or an import error, report the exact error
and stop — do not proceed to the coverage phases.

---

## Phase 2 — Route Coverage

Using the routes you read in the pre-flight step, build a coverage table:

| Route | Methods | Test file | Covered? |
|-------|---------|-----------|----------|

A route is **covered** only if at least one test sends a real HTTP request to it
(`client.get(...)` or `client.post(...)`). Read every file in `tests/` to verify.
Function names appearing in test files are not enough — the HTTP call must be present.

Known gaps to confirm in the current suite:

- `GET /` (landing) — check `tests/test_landing.py` for coverage
- `GET /profile?date_from=&date_to=` variants — check if date-filtered profile requests are tested
- The `date_from > date_to` validation branch in `/profile` — check if tested

---

## Phase 3 — Query Function Coverage

List every public function in `database/queries.py`. For each function note:

1. **Unit tests present** — imported and called directly in at least one test
2. **Date-filter tested** — called with `date_from` and `date_to` arguments in at least one test

Then check `database/db.py` for these two functions and note if they have any unit tests:
- `create_user` (used by the untested `/register` route)
- `get_user_by_email` (used by the untested `/login` route)

---

## Phase 4 — Code Quality Checks

Run each check against the real file. Do not infer — read the file or grep it.

### 4a. Secret key — CRITICAL
- File: `app.py`
- Check: Is `app.secret_key` assigned a static string literal?
- Flag if yes. Recommended fix: read from environment variable using
  `os.environ.get("SECRET_KEY", "fallback-only-for-dev")`.

### 4b. DB isolation in test_backend_connection.py — MEDIUM
- File: `tests/test_backend_connection.py`
- Check: Do the fixtures patch `DB_PATH` with a temp file, or do they call `get_db()`
  against the real `spendly.db`?
- Flag if using the real DB. This makes the suite fragile — count and total assertions
  break if `spendly.db` is absent or its seed data changes. Recommended fix: adopt the
  same `isolated_db` fixture pattern used in the other three test files.

### 4c. Session not cleared before login — MEDIUM
- File: `app.py`, the `login()` route
- Check: Does the login route call `session.clear()` before setting `session["user_id"]`?
- Flag if absent. Without this, a pre-existing session value survives a new login.
  Recommended fix: add `session.clear()` immediately before `session["user_id"] = user["id"]`.

### 4d. No CSRF protection — LOW
- Files: `app.py`, `templates/*.html`
- Check: Is Flask-WTF or any CSRF token used in any form?
- Flag if absent. Recommended fix: install `flask-wtf`, initialize
  `CSRFProtect(app)`, and add `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` 
  to every POST form (or use `{{ form.hidden_tag() }}` with WTForms).

### 4e. Hardcoded hex color in CSS — LOW
- Grep `static/css/` for hex color literals (`#[0-9a-fA-F]{3,6}`) that appear outside
  a `:root { }` block and outside a comment.
- Known violation: `static/css/style.css` — `.auth-error` has `border: 1px solid #f5c6c2`
  instead of using `var(--border)` or `var(--danger-light)`.
- Report any others found.

---

## Phase 5 — Report

Present the full report in this structure. Use the exact headings.

---

### Quality Analysis Report — Spendly

**Test suite:** N passed · N failed · N total — [PASS / FAIL]
**Run time:** [duration]

---

#### Route Coverage

[Table from Phase 2, one row per route]

**Uncovered routes:** [list]

---

#### Query Function Coverage

[Table: function | unit tests | date-filter tests]

**Functions missing date-filter tests:** [list]
**Functions with no unit tests at all:** [list]

---

#### Code Quality Findings

Format each as:

> **[CRITICAL / MEDIUM / LOW]** `filename:line` — one-sentence issue.  
> Fix: one-sentence recommendation.

List all findings from Phase 4. If a check passes cleanly, omit it from this section.

---

#### Priority Action Plan

Ordered checklist, severity-first:

- [ ] [CRITICAL items first]
- [ ] [MEDIUM items]
- [ ] [LOW items and coverage gaps]

Number each item — the user will refer to them by number when requesting fixes.

---

#### Overall Health

Choose one:
- **HEALTHY** — all tests pass, no CRITICAL or MEDIUM issues, fewer than 3 uncovered routes
- **NEEDS ATTENTION** — tests pass but CRITICAL or MEDIUM issues present, or 3+ uncovered routes
- **FAILING** — any test failures

---

## Phase 6 — Offer to Fix

After presenting the report, ask:

"Which action plan items do you want me to implement? Name the numbers or say 'all'."

Wait for an explicit response before editing any file.

---

## Rules

- Run pytest before reading any code — a failing test suite changes every priority.
- Never count a route as covered unless a real HTTP call (`client.get` / `client.post`) appears in a test.
- Never edit files before the user approves.
- If a file is missing or unreadable, say so explicitly instead of skipping silently.
- If pytest fails to collect (import error, syntax error), stop at Phase 1 — do not guess at coverage.
- Keep the report in the exact structure above — the user can scan it without re-reading the analysis.
