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


@pytest.fixture
def seed_expense_id(isolated_db, demo_user_id):
    """Return the id of the first seeded expense for the demo user."""
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE user_id = ? ORDER BY id ASC LIMIT 1",
            (demo_user_id,),
        ).fetchone()
        conn.close()
        return row["id"]


# ------------------------------------------------------------------ #
# Unit tests — get_expense_by_id                                      #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_valid(isolated_db, demo_user_id, seed_expense_id):
    from database.queries import get_expense_by_id
    with patch.object(db_module, "DB_PATH", isolated_db):
        result = get_expense_by_id(seed_expense_id, demo_user_id)
    assert result is not None
    assert result["id"] == seed_expense_id
    assert "amount" in result
    assert "category" in result
    assert "date" in result
    assert "description" in result


def test_get_expense_by_id_wrong_user(isolated_db, seed_expense_id):
    from database.queries import get_expense_by_id
    with patch.object(db_module, "DB_PATH", isolated_db):
        result = get_expense_by_id(seed_expense_id, user_id=999999)
    assert result is None


def test_get_expense_by_id_nonexistent(isolated_db, demo_user_id):
    from database.queries import get_expense_by_id
    with patch.object(db_module, "DB_PATH", isolated_db):
        result = get_expense_by_id(expense_id=999999, user_id=demo_user_id)
    assert result is None


# ------------------------------------------------------------------ #
# Unit tests — update_expense                                         #
# ------------------------------------------------------------------ #

def test_update_expense_valid(isolated_db, demo_user_id, seed_expense_id):
    from database.queries import update_expense, get_expense_by_id
    with patch.object(db_module, "DB_PATH", isolated_db):
        update_expense(seed_expense_id, demo_user_id, 99.0, "Health", "2026-11-01", "Updated desc")
        result = get_expense_by_id(seed_expense_id, demo_user_id)
    assert result["amount"] == 99.0
    assert result["category"] == "Health"
    assert result["date"] == "2026-11-01"
    assert result["description"] == "Updated desc"


def test_update_expense_wrong_user_no_change(isolated_db, demo_user_id, seed_expense_id):
    from database.queries import update_expense, get_expense_by_id
    with patch.object(db_module, "DB_PATH", isolated_db):
        original = get_expense_by_id(seed_expense_id, demo_user_id)
        update_expense(seed_expense_id, user_id=999999, amount=1.0,
                       category="Other", date="2026-01-01", description=None)
        after = get_expense_by_id(seed_expense_id, demo_user_id)
    assert after["amount"] == original["amount"]
    assert after["category"] == original["category"]


# ------------------------------------------------------------------ #
# Route tests                                                         #
# ------------------------------------------------------------------ #

def test_get_edit_unauthenticated_redirects(client, seed_expense_id):
    r = client.get(f"/expenses/{seed_expense_id}/edit")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_get_edit_own_expense_ok(auth_client, seed_expense_id):
    r = auth_client.get(f"/expenses/{seed_expense_id}/edit")
    assert r.status_code == 200
    html = r.data.decode()
    assert "Edit Expense" in html
    assert "Save Changes" in html
    # all 7 categories present
    for cat in CATEGORIES:
        assert cat in html


def test_get_edit_other_user_expense_404(client, isolated_db):
    from werkzeug.security import generate_password_hash
    # create a second user and give them an expense
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Other User", "other@spendly.com", generate_password_hash("pass1234")),
        )
        other_uid = cur.lastrowid
        cur2 = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_uid, 10.0, "Food", "2026-10-12", "Other's expense"),
        )
        other_expense_id = cur2.lastrowid
        conn.commit()
        conn.close()

    # log in as demo user
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    r = client.get(f"/expenses/{other_expense_id}/edit")
    assert r.status_code == 404


def test_get_edit_nonexistent_expense_404(auth_client):
    r = auth_client.get("/expenses/999999/edit")
    assert r.status_code == 404


def test_post_edit_unauthenticated_redirects(client, seed_expense_id):
    r = client.post(f"/expenses/{seed_expense_id}/edit", data={
        "amount": "20.00", "category": "Food", "date": "2026-10-12", "description": "",
    })
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_post_edit_valid_redirects_and_updates(auth_client, isolated_db, seed_expense_id, demo_user_id):
    r = auth_client.post(f"/expenses/{seed_expense_id}/edit", data={
        "amount": "77.77",
        "category": "Health",
        "date": "2026-11-15",
        "description": "Updated",
    })
    assert r.status_code == 302
    assert "/profile" in r.headers["Location"]

    from database.queries import get_expense_by_id
    with patch.object(db_module, "DB_PATH", isolated_db):
        row = get_expense_by_id(seed_expense_id, demo_user_id)
    assert row["amount"] == 77.77
    assert row["category"] == "Health"
    assert row["date"] == "2026-11-15"
    assert row["description"] == "Updated"


def test_post_edit_other_user_expense_404(client, isolated_db):
    from werkzeug.security import generate_password_hash
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Other2", "other2@spendly.com", generate_password_hash("pass1234")),
        )
        other_uid = cur.lastrowid
        cur2 = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_uid, 5.0, "Food", "2026-10-12", None),
        )
        other_expense_id = cur2.lastrowid
        conn.commit()
        conn.close()

    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    r = client.post(f"/expenses/{other_expense_id}/edit", data={
        "amount": "1.00", "category": "Food", "date": "2026-10-12", "description": "",
    })
    assert r.status_code == 404


def test_post_edit_zero_amount_fails(auth_client, seed_expense_id):
    r = auth_client.post(f"/expenses/{seed_expense_id}/edit", data={
        "amount": "0", "category": "Food", "date": "2026-10-12", "description": "",
    })
    assert r.status_code == 200
    assert "positive number" in r.data.decode()


def test_post_edit_non_numeric_amount_fails(auth_client, seed_expense_id):
    r = auth_client.post(f"/expenses/{seed_expense_id}/edit", data={
        "amount": "abc", "category": "Food", "date": "2026-10-12", "description": "",
    })
    assert r.status_code == 200
    assert "positive number" in r.data.decode()


def test_post_edit_invalid_category_fails(auth_client, seed_expense_id):
    r = auth_client.post(f"/expenses/{seed_expense_id}/edit", data={
        "amount": "10.00", "category": "InvalidCat", "date": "2026-10-12", "description": "",
    })
    assert r.status_code == 200
    assert "valid category" in r.data.decode()


def test_post_edit_invalid_date_fails(auth_client, seed_expense_id):
    r = auth_client.post(f"/expenses/{seed_expense_id}/edit", data={
        "amount": "10.00", "category": "Food", "date": "not-a-date", "description": "",
    })
    assert r.status_code == 200
    assert "valid date" in r.data.decode()


def test_post_edit_no_description_succeeds(auth_client, isolated_db, seed_expense_id, demo_user_id):
    r = auth_client.post(f"/expenses/{seed_expense_id}/edit", data={
        "amount": "10.00", "category": "Food", "date": "2026-10-12", "description": "",
    })
    assert r.status_code == 302

    from database.queries import get_expense_by_id
    with patch.object(db_module, "DB_PATH", isolated_db):
        row = get_expense_by_id(seed_expense_id, demo_user_id)
    assert row["description"] is None
