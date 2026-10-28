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


@pytest.fixture
def auth_client(client):
    """Test client that is already authenticated as the seed demo user."""
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    return client


# ------------------------------------------------------------------ #
# Tests — GET /logout                                                 #
# ------------------------------------------------------------------ #

def test_logout_redirects_to_landing(auth_client):
    r = auth_client.get("/logout", follow_redirects=False)
    assert r.status_code == 302, "Logout must redirect (302)"
    assert r.headers["Location"].endswith("/"), (
        "Logout must redirect to the landing page (/)"
    )


def test_logout_clears_user_id_from_session(auth_client):
    # Confirm user_id is in session before logout
    with auth_client.session_transaction() as sess:
        assert "user_id" in sess, "user_id must be in session before logout"

    auth_client.get("/logout")

    with auth_client.session_transaction() as sess:
        assert "user_id" not in sess, "user_id must be removed from session after logout"


def test_logout_clears_entire_session(auth_client):
    auth_client.get("/logout")
    with auth_client.session_transaction() as sess:
        assert len(sess) == 0, "Session must be fully cleared after logout"


def test_logout_after_logout_profile_redirects_to_login(auth_client):
    """Once logged out, accessing /profile must require re-authentication."""
    auth_client.get("/logout")
    r = auth_client.get("/profile", follow_redirects=False)
    assert r.status_code == 302, "Profile must redirect after logout"
    assert "/login" in r.headers["Location"], "Post-logout profile access must redirect to /login"


def test_logout_unauthenticated_still_redirects_to_landing(client):
    """Logout on an unauthenticated client must still succeed and redirect to /."""
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 302, "Logout without prior login must still redirect (302)"
    assert r.headers["Location"].endswith("/"), (
        "Unauthenticated logout must redirect to landing page (/)"
    )


def test_logout_landing_page_shows_sign_in_link(auth_client):
    """After logout the landing page must present unauthenticated navigation."""
    r = auth_client.get("/logout", follow_redirects=True)
    html = r.data.decode()
    assert "Sign in" in html, "Landing page after logout must show 'Sign in' link"


def test_logout_re_login_sets_new_session(client):
    """User can log in again after logging out, establishing a fresh session."""
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    client.get("/logout")

    with client.session_transaction() as sess:
        assert "user_id" not in sess, "Session must be empty after logout"

    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    with client.session_transaction() as sess:
        assert "user_id" in sess, "Re-login after logout must create a new session"
