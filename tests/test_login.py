import sys
import os
import tempfile
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database.db as db_module
from app import app


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def isolated_db():
    """Fresh temp SQLite DB, initialised and seeded.

    seed_db() creates: demo@spendly.com / demo123
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
# Tests — GET /login                                                  #
# ------------------------------------------------------------------ #

def test_get_login_returns_200(client):
    r = client.get("/login")
    assert r.status_code == 200, "GET /login must return HTTP 200"


def test_get_login_renders_form(client):
    r = client.get("/login")
    html = r.data.decode()
    assert "Welcome back" in html, "Login page must show 'Welcome back' heading"


def test_get_login_has_email_field(client):
    r = client.get("/login")
    html = r.data.decode()
    assert 'name="email"' in html, "Login form must have an 'email' input field"


def test_get_login_has_password_field(client):
    r = client.get("/login")
    html = r.data.decode()
    assert 'name="password"' in html, "Login form must have a 'password' input field"


def test_get_login_has_sign_in_button(client):
    r = client.get("/login")
    html = r.data.decode()
    assert "Sign in" in html, "Login page must contain a 'Sign in' button"


# ------------------------------------------------------------------ #
# Tests — POST /login happy path                                      #
# ------------------------------------------------------------------ #

def test_post_login_valid_credentials_redirects(client):
    r = client.post("/login", data={
        "email": "demo@spendly.com",
        "password": "demo123",
    }, follow_redirects=False)
    assert r.status_code == 302, "Valid login must redirect (302)"
    assert r.headers["Location"].endswith("/"), (
        "Successful login must redirect to the landing page (/)"
    )


def test_post_login_valid_credentials_sets_session(client):
    client.post("/login", data={
        "email": "demo@spendly.com",
        "password": "demo123",
    })
    with client.session_transaction() as sess:
        assert "user_id" in sess, "Successful login must set session['user_id']"
        assert isinstance(sess["user_id"], int), "session['user_id'] must be an integer"
        assert sess["user_id"] > 0, "session['user_id'] must be a positive integer"


def test_post_login_session_user_id_matches_db(client, isolated_db):
    client.post("/login", data={
        "email": "demo@spendly.com",
        "password": "demo123",
    })
    with patch.object(db_module, "DB_PATH", isolated_db):
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
        conn.close()
    with client.session_transaction() as sess:
        assert sess["user_id"] == row["id"], (
            "session['user_id'] must match the user's actual DB id"
        )


# ------------------------------------------------------------------ #
# Tests — POST /login failure paths                                   #
# ------------------------------------------------------------------ #

def test_post_login_wrong_password_flashes_error(client):
    r = client.post("/login", data={
        "email": "demo@spendly.com",
        "password": "wrongpassword",
    })
    assert r.status_code == 200, "Wrong password must re-render login form (200)"
    html = r.data.decode()
    assert "Invalid email or password." in html, (
        "Wrong password must flash 'Invalid email or password.'"
    )


def test_post_login_wrong_password_does_not_set_session(client):
    client.post("/login", data={
        "email": "demo@spendly.com",
        "password": "wrongpassword",
    })
    with client.session_transaction() as sess:
        assert "user_id" not in sess, "Failed login must not set session['user_id']"


def test_post_login_unknown_email_flashes_error(client):
    r = client.post("/login", data={
        "email": "nobody@nowhere.com",
        "password": "somepassword",
    })
    assert r.status_code == 200, "Unknown email must re-render login form (200)"
    html = r.data.decode()
    assert "Invalid email or password." in html, (
        "Unknown email must flash 'Invalid email or password.'"
    )


def test_post_login_unknown_email_does_not_set_session(client):
    client.post("/login", data={
        "email": "ghost@nowhere.com",
        "password": "pass1234",
    })
    with client.session_transaction() as sess:
        assert "user_id" not in sess, "Login with unknown email must not set session['user_id']"


def test_post_login_missing_email_flashes_error(client):
    r = client.post("/login", data={
        "email": "",
        "password": "demo123",
    })
    assert r.status_code == 200, "Missing email must re-render login form (200)"
    html = r.data.decode()
    assert "Invalid email or password." in html, (
        "Missing email must flash 'Invalid email or password.'"
    )


def test_post_login_missing_password_flashes_error(client):
    r = client.post("/login", data={
        "email": "demo@spendly.com",
        "password": "",
    })
    assert r.status_code == 200, "Missing password must re-render login form (200)"
    html = r.data.decode()
    assert "Invalid email or password." in html, (
        "Missing password must flash 'Invalid email or password.'"
    )


def test_post_login_missing_both_fields_flashes_error(client):
    r = client.post("/login", data={
        "email": "",
        "password": "",
    })
    assert r.status_code == 200, "All-empty POST must re-render login form (200)"
    html = r.data.decode()
    assert "Invalid email or password." in html, (
        "Empty credentials must flash 'Invalid email or password.'"
    )


# ------------------------------------------------------------------ #
# Tests — SQL injection safety                                        #
# ------------------------------------------------------------------ #

def test_post_login_sql_injection_email_is_safe(client):
    """Parameterised queries must handle SQL injection attempts without crashing."""
    r = client.post("/login", data={
        "email": "' OR '1'='1",
        "password": "anything",
    })
    assert r.status_code == 200, "SQL injection attempt must return 200 (re-render), not crash"
    html = r.data.decode()
    assert "Invalid email or password." in html, (
        "SQL injection attempt must fail authentication and flash the standard error"
    )
