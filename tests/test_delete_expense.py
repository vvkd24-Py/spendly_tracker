import sys
import os
import tempfile
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database.db as db_module
from app import app


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
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE user_id = ? ORDER BY id ASC LIMIT 1",
            (demo_user_id,),
        ).fetchone()
        conn.close()
        return row["id"]


# ------------------------------------------------------------------ #
# Unit tests — delete_expense                                         #
# ------------------------------------------------------------------ #

def test_delete_expense_removes_row(isolated_db, demo_user_id, seed_expense_id):
    from database.queries import delete_expense
    with patch.object(db_module, "DB_PATH", isolated_db):
        delete_expense(seed_expense_id, demo_user_id)
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE id = ?", (seed_expense_id,)
        ).fetchone()
        conn.close()
    assert row is None


def test_delete_expense_wrong_user_no_change(isolated_db, demo_user_id, seed_expense_id):
    from database.queries import delete_expense
    with patch.object(db_module, "DB_PATH", isolated_db):
        delete_expense(seed_expense_id, user_id=999999)
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE id = ?", (seed_expense_id,)
        ).fetchone()
        conn.close()
    assert row is not None


def test_delete_expense_nonexistent_no_error(isolated_db, demo_user_id):
    from database.queries import delete_expense
    with patch.object(db_module, "DB_PATH", isolated_db):
        delete_expense(expense_id=999999, user_id=demo_user_id)
        count = db_module.get_db().execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    assert count == 8


# ------------------------------------------------------------------ #
# Route tests                                                         #
# ------------------------------------------------------------------ #

def test_post_delete_unauthenticated_redirects(client, seed_expense_id):
    r = client.post(f"/expenses/{seed_expense_id}/delete")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_post_delete_own_expense_redirects_and_removes(auth_client, isolated_db, seed_expense_id, demo_user_id):
    r = auth_client.post(f"/expenses/{seed_expense_id}/delete")
    assert r.status_code == 302
    assert "/profile" in r.headers["Location"]

    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE id = ?", (seed_expense_id,)
        ).fetchone()
        conn.close()
    assert row is None


def test_post_delete_other_user_expense_404(client, isolated_db):
    from werkzeug.security import generate_password_hash
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

    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    r = client.post(f"/expenses/{other_expense_id}/delete")
    assert r.status_code == 404

    # row must still exist
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE id = ?", (other_expense_id,)
        ).fetchone()
        conn.close()
    assert row is not None


def test_post_delete_nonexistent_expense_404(auth_client):
    r = auth_client.post("/expenses/999999/delete")
    assert r.status_code == 404


def test_get_delete_returns_405(auth_client, seed_expense_id):
    r = auth_client.get(f"/expenses/{seed_expense_id}/delete")
    assert r.status_code == 405
