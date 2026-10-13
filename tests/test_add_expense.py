import sys
import os
import tempfile
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database.db as db_module
from app import app, CATEGORIES


# ------------------------------------------------------------------ #
# Fixtures — isolated temp database per test function                 #
# ------------------------------------------------------------------ #

@pytest.fixture
def isolated_db():
    """Fresh temp SQLite DB, seeded, then yielded as a path (no lingering patch)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    with patch.object(db_module, "DB_PATH", tmp.name):
        db_module.init_db()
        db_module.seed_db()
    yield tmp.name
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest.fixture
def client(isolated_db):
    app.config["TESTING"] = True
    with patch.object(db_module, "DB_PATH", isolated_db):
        with app.test_client() as c:
            yield c


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    return client


@pytest.fixture
def demo_user_id(isolated_db):
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
        conn.close()
        return row["id"]


# ------------------------------------------------------------------ #
# Unit tests                                                          #
# ------------------------------------------------------------------ #

def test_insert_expense_returns_id(isolated_db, demo_user_id):
    from database.queries import insert_expense
    with patch.object(db_module, "DB_PATH", isolated_db):
        expense_id = insert_expense(demo_user_id, 42.50, "Food", "2026-10-12", "Test unit expense")
        assert isinstance(expense_id, int)
        assert expense_id > 0

        conn = db_module.get_db()
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        conn.close()
    assert row is not None
    assert row["amount"] == 42.50
    assert row["category"] == "Food"
    assert row["description"] == "Test unit expense"


def test_insert_expense_null_description(isolated_db, demo_user_id):
    from database.queries import insert_expense
    with patch.object(db_module, "DB_PATH", isolated_db):
        expense_id = insert_expense(demo_user_id, 10.00, "Transport", "2026-10-12", None)
        conn = db_module.get_db()
        row = conn.execute("SELECT description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        conn.close()
    assert row["description"] is None


# ------------------------------------------------------------------ #
# Route tests                                                         #
# ------------------------------------------------------------------ #

def test_get_add_expense_unauthenticated_redirects(client):
    r = client.get("/expenses/add")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_get_add_expense_authenticated_ok(auth_client):
    r = auth_client.get("/expenses/add")
    assert r.status_code == 200
    html = r.data.decode()
    assert "Add Expense" in html


def test_get_add_expense_has_all_categories(auth_client):
    r = auth_client.get("/expenses/add")
    html = r.data.decode()
    for cat in CATEGORIES:
        assert cat in html


def test_post_valid_expense_redirects_to_profile(auth_client):
    r = auth_client.post("/expenses/add", data={
        "amount": "55.00",
        "category": "Food",
        "date": "2026-10-12",
        "description": "Test meal",
    })
    assert r.status_code == 302
    assert "/profile" in r.headers["Location"]


def test_post_zero_amount_fails(auth_client):
    r = auth_client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-10-12",
        "description": "",
    })
    assert r.status_code == 200
    assert "positive number" in r.data.decode()


def test_post_negative_amount_fails(auth_client):
    r = auth_client.post("/expenses/add", data={
        "amount": "-10",
        "category": "Food",
        "date": "2026-10-12",
        "description": "",
    })
    assert r.status_code == 200
    assert "positive number" in r.data.decode()


def test_post_non_numeric_amount_fails(auth_client):
    r = auth_client.post("/expenses/add", data={
        "amount": "abc",
        "category": "Food",
        "date": "2026-10-12",
        "description": "",
    })
    assert r.status_code == 200
    assert "positive number" in r.data.decode()


def test_post_invalid_category_fails(auth_client):
    r = auth_client.post("/expenses/add", data={
        "amount": "20.00",
        "category": "InvalidCat",
        "date": "2026-10-12",
        "description": "",
    })
    assert r.status_code == 200
    assert "valid category" in r.data.decode()


def test_post_invalid_date_fails(auth_client):
    r = auth_client.post("/expenses/add", data={
        "amount": "20.00",
        "category": "Food",
        "date": "not-a-date",
        "description": "",
    })
    assert r.status_code == 200
    assert "valid date" in r.data.decode()


def test_post_no_description_succeeds(auth_client, isolated_db, demo_user_id):
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        count_before = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (demo_user_id,)
        ).fetchone()[0]
        conn.close()

    r = auth_client.post("/expenses/add", data={
        "amount": "15.00",
        "category": "Other",
        "date": "2026-10-12",
        "description": "",
    })
    assert r.status_code == 302

    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        count_after = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (demo_user_id,)
        ).fetchone()[0]
        last = conn.execute(
            "SELECT description FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (demo_user_id,),
        ).fetchone()
        conn.close()
    assert count_after == count_before + 1
    assert last["description"] is None
