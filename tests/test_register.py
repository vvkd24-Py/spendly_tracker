import sys
import os
import tempfile
import pytest
from unittest.mock import patch
from werkzeug.security import check_password_hash

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database.db as db_module
from app import app


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def isolated_db():
    """Fresh temp SQLite DB, initialised and seeded, yielded as a path.

    seed_db() creates demo@spendly.com — used to test duplicate-email rejection.
    """
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


# ------------------------------------------------------------------ #
# Tests — GET /register                                               #
# ------------------------------------------------------------------ #

def test_get_register_returns_200(client):
    r = client.get("/register")
    assert r.status_code == 200, "GET /register must return HTTP 200"


def test_get_register_renders_form(client):
    r = client.get("/register")
    html = r.data.decode()
    assert "Create your account" in html, "Register page must show 'Create your account' heading"


def test_get_register_has_name_field(client):
    r = client.get("/register")
    html = r.data.decode()
    assert 'name="name"' in html, "Register form must have a 'name' input field"


def test_get_register_has_email_field(client):
    r = client.get("/register")
    html = r.data.decode()
    assert 'name="email"' in html, "Register form must have an 'email' input field"


def test_get_register_has_password_fields(client):
    r = client.get("/register")
    html = r.data.decode()
    assert 'name="password"' in html, "Register form must have a 'password' field"
    assert 'name="confirm_password"' in html, "Register form must have a 'confirm_password' field"


# ------------------------------------------------------------------ #
# Tests — POST /register happy path                                   #
# ------------------------------------------------------------------ #

def test_post_register_valid_data_redirects_to_login(client):
    r = client.post("/register", data={
        "name": "Alice Tester",
        "email": "alice@example.com",
        "password": "secure123",
        "confirm_password": "secure123",
    }, follow_redirects=False)
    assert r.status_code == 302, "Successful registration must redirect (302)"
    assert "/login" in r.headers["Location"], "Redirect after registration must point to /login"


def test_post_register_creates_user_in_db(client, isolated_db):
    client.post("/register", data={
        "name": "Bob Builder",
        "email": "bob@example.com",
        "password": "password1",
        "confirm_password": "password1",
    })
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id, name, email FROM users WHERE email = ?",
            ("bob@example.com",)
        ).fetchone()
        conn.close()
    assert row is not None, "Registered user must be persisted in the database"
    assert row["name"] == "Bob Builder", "Stored name must match submitted name"


def test_post_register_stores_hashed_password(client, isolated_db):
    client.post("/register", data={
        "name": "Carol Hash",
        "email": "carol@example.com",
        "password": "myplaintext",
        "confirm_password": "myplaintext",
    })
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            ("carol@example.com",)
        ).fetchone()
        conn.close()
    assert row is not None, "User must exist in the database after registration"
    assert row["password_hash"] != "myplaintext", "Password must not be stored as plaintext"
    assert check_password_hash(row["password_hash"], "myplaintext"), (
        "Stored hash must verify correctly against the original password"
    )


def test_post_register_flashes_account_created_message(client):
    r = client.post("/register", data={
        "name": "Dave Success",
        "email": "dave@example.com",
        "password": "abc12345",
        "confirm_password": "abc12345",
    }, follow_redirects=True)
    html = r.data.decode()
    assert "Account created" in html, "Flash message 'Account created' must appear after successful registration"


# ------------------------------------------------------------------ #
# Tests — POST /register validation errors                            #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("missing_field,data", [
    ("name", {
        "name": "",
        "email": "test@example.com",
        "password": "pass1234",
        "confirm_password": "pass1234",
    }),
    ("email", {
        "name": "Test User",
        "email": "",
        "password": "pass1234",
        "confirm_password": "pass1234",
    }),
    ("password", {
        "name": "Test User",
        "email": "test@example.com",
        "password": "",
        "confirm_password": "pass1234",
    }),
    ("confirm_password", {
        "name": "Test User",
        "email": "test@example.com",
        "password": "pass1234",
        "confirm_password": "",
    }),
])
def test_post_register_missing_field_flashes_error(client, missing_field, data):
    r = client.post("/register", data=data)
    assert r.status_code == 200, f"Missing '{missing_field}' must re-render form (200), not redirect"
    html = r.data.decode()
    assert "All fields are required." in html, (
        f"Missing '{missing_field}' must flash 'All fields are required.'"
    )


def test_post_register_mismatched_passwords_flashes_error(client):
    r = client.post("/register", data={
        "name": "Eve Mismatch",
        "email": "eve@example.com",
        "password": "password1",
        "confirm_password": "password2",
    })
    assert r.status_code == 200, "Mismatched passwords must re-render form (200)"
    html = r.data.decode()
    assert "Passwords do not match." in html, "Mismatched passwords must flash 'Passwords do not match.'"


def test_post_register_duplicate_email_flashes_error(client):
    """demo@spendly.com already exists from seed_db()."""
    r = client.post("/register", data={
        "name": "Duplicate Demo",
        "email": "demo@spendly.com",
        "password": "anypassword",
        "confirm_password": "anypassword",
    })
    assert r.status_code == 200, "Duplicate email must re-render form (200)"
    html = r.data.decode()
    assert "Email already registered." in html, "Duplicate email must flash 'Email already registered.'"


def test_post_register_missing_all_fields_rerendered_form(client):
    r = client.post("/register", data={
        "name": "",
        "email": "",
        "password": "",
        "confirm_password": "",
    })
    assert r.status_code == 200, "All-empty POST must re-render form (200)"
    html = r.data.decode()
    assert "Create your account" in html, "Re-rendered form must show the register page heading"
