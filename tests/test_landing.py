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
    """Fresh temp SQLite DB, initialised and seeded, yielded as a path."""
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
# Tests — GET /                                                       #
# ------------------------------------------------------------------ #

def test_landing_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200, "Landing page must return HTTP 200"


def test_landing_renders_hero_title(client):
    r = client.get("/")
    html = r.data.decode()
    assert "Know where your" in html, "Hero title text 'Know where your' must be in landing page"


def test_landing_renders_cta_button(client):
    r = client.get("/")
    html = r.data.decode()
    assert "Start tracking free" in html, "Primary CTA button text must appear on landing page"


def test_landing_renders_feature_section(client):
    r = client.get("/")
    html = r.data.decode()
    assert "Log expenses instantly" in html, "Features section must be rendered on landing page"


def test_landing_renders_register_link(client):
    r = client.get("/")
    html = r.data.decode()
    assert "/register" in html, "Landing page must link to /register"


def test_landing_renders_login_link(client):
    r = client.get("/")
    html = r.data.decode()
    assert "/login" in html, "Landing page must link to /login"


def test_landing_contains_brand_name(client):
    r = client.get("/")
    html = r.data.decode()
    assert "Spendly" in html, "Brand name 'Spendly' must appear on landing page"


def test_landing_contains_ready_to_take_control_cta(client):
    r = client.get("/")
    html = r.data.decode()
    assert "Ready to take control?" in html, "CTA section heading must be present on landing page"
