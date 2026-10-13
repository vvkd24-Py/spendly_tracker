import sys
import sqlite3
import pytest

sys.path.insert(0, ".")

from app import app
from database.db import get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def demo_user_id():
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    return row["id"]


@pytest.fixture
def empty_user_id():
    """Register a fresh user with no expenses and return their id."""
    conn = get_db()
    from werkzeug.security import generate_password_hash
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty_test@spendly.com", generate_password_hash("pass1234")),
    )
    uid = cur.lastrowid
    conn.commit()
    conn.close()
    yield uid
    # cleanup
    conn2 = get_db()
    conn2.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn2.commit()
    conn2.close()


# ------------------------------------------------------------------ #
# Unit tests — get_user_by_id                                        #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(demo_user_id):
    result = get_user_by_id(demo_user_id)
    assert result is not None
    assert result["name"] == "Demo User"
    assert result["email"] == "demo@spendly.com"
    assert "member_since" in result
    assert result["member_since"] != ""


def test_get_user_by_id_nonexistent():
    result = get_user_by_id(999999)
    assert result is None


# ------------------------------------------------------------------ #
# Unit tests — get_summary_stats                                     #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(demo_user_id):
    result = get_summary_stats(demo_user_id)
    assert result["total_spent"] == "346.24"
    assert result["transaction_count"] == 8
    assert result["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(empty_user_id):
    result = get_summary_stats(empty_user_id)
    assert result == {"total_spent": "0.00", "transaction_count": 0, "top_category": "—"}


# ------------------------------------------------------------------ #
# Unit tests — get_recent_transactions                               #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_with_expenses(demo_user_id):
    result = get_recent_transactions(demo_user_id)
    assert len(result) == 8
    for tx in result:
        assert "date" in tx
        assert "description" in tx
        assert "category" in tx
        assert "amount" in tx
    # newest-first
    dates = [tx["date"] for tx in result]
    assert dates == sorted(dates, reverse=True)


def test_get_recent_transactions_no_expenses(empty_user_id):
    result = get_recent_transactions(empty_user_id)
    assert result == []


# ------------------------------------------------------------------ #
# Unit tests — get_category_breakdown                                #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_with_expenses(demo_user_id):
    result = get_category_breakdown(demo_user_id)
    assert len(result) == 7
    # ordered by amount descending
    amounts = [item["amount"] for item in result]
    assert amounts == sorted(amounts, reverse=True)
    # pct values are integers summing to 100
    for item in result:
        assert isinstance(item["pct"], int)
    assert sum(item["pct"] for item in result) == 100
    assert all("name" in item and "amount" in item and "pct" in item for item in result)


def test_get_category_breakdown_no_expenses(empty_user_id):
    result = get_category_breakdown(empty_user_id)
    assert result == []


# ------------------------------------------------------------------ #
# Route tests                                                         #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated(client):
    r = client.get("/profile", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_profile_authenticated_seed_user(client, demo_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = demo_user_id

    r = client.get("/profile")
    assert r.status_code == 200
    html = r.data.decode()

    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html
    assert "346.24" in html
    assert "Bills" in html

    # 8 transaction rows (count <tr> minus header)
    assert html.count("<tr>") - 1 >= 8

    # 7 category breakdown rows
    assert html.count("breakdown-row") >= 7

    # newest date appears before oldest in the transactions table
    table_start = html.find("transactions-table")
    assert table_start != -1, "transactions-table not found"
    pos_newest = html.find("2026-10-12", table_start)
    pos_oldest = html.find("2026-10-01", table_start)
    assert pos_newest < pos_oldest, "Transactions not in newest-first order"
