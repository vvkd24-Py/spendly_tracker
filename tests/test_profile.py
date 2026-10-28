import sys
import os
import tempfile
import pytest
from datetime import date
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

    seed_db() creates: demo@spendly.com / demo123, plus 8 sample expenses.
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
    """Test client authenticated as the seed demo user."""
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    return client


# ------------------------------------------------------------------ #
# Tests — auth guard                                                  #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects_to_login(client):
    r = client.get("/profile", follow_redirects=False)
    assert r.status_code == 302, "Unauthenticated /profile must redirect (302)"
    assert "/login" in r.headers["Location"], "Unauthenticated /profile must redirect to /login"


def test_profile_unauthenticated_does_not_return_200(client):
    r = client.get("/profile", follow_redirects=False)
    assert r.status_code != 200, "Unauthenticated /profile must not return 200"


# ------------------------------------------------------------------ #
# Tests — authenticated happy path                                    #
# ------------------------------------------------------------------ #

def test_profile_authenticated_returns_200(auth_client):
    r = auth_client.get("/profile")
    assert r.status_code == 200, "Authenticated GET /profile must return HTTP 200"


def test_profile_renders_user_name(auth_client):
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert "Demo User" in html, "Profile page must display the logged-in user's name"


def test_profile_renders_user_email(auth_client):
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert "demo@spendly.com" in html, "Profile page must display the logged-in user's email"


def test_profile_renders_stats_section(auth_client):
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert "Total Spent" in html, "Profile page must render the stats section with 'Total Spent'"


def test_profile_renders_transactions_table(auth_client):
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert "transactions-table" in html, "Profile page must render a transactions table"


def test_profile_renders_category_breakdown(auth_client):
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert "breakdown-row" in html, "Profile page must render category breakdown rows"


def test_profile_renders_preset_filter_links(auth_client):
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert "This Month" in html, "Profile page must render 'This Month' preset filter link"
    assert "Last 3 Months" in html, "Profile page must render 'Last 3 Months' preset filter link"
    assert "Last 6 Months" in html, "Profile page must render 'Last 6 Months' preset filter link"
    assert "All Time" in html, "Profile page must render 'All Time' preset filter link"


def test_profile_renders_filter_form(auth_client):
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert 'name="date_from"' in html, "Profile page must render the date_from filter input"
    assert 'name="date_to"' in html, "Profile page must render the date_to filter input"


# ------------------------------------------------------------------ #
# Tests — date filter: valid params                                   #
# ------------------------------------------------------------------ #

def test_profile_valid_date_range_returns_200(auth_client):
    r = auth_client.get("/profile?date_from=2026-10-01&date_to=2026-10-31")
    assert r.status_code == 200, "Valid date_from/date_to params must return HTTP 200"


def test_profile_date_filter_restricts_results(auth_client):
    """Filter to a single day that only matches one seeded expense (2026-10-01 = Groceries)."""
    r = auth_client.get("/profile?date_from=2026-10-01&date_to=2026-10-01")
    assert r.status_code == 200, "Single-day date filter must return HTTP 200"
    html = r.data.decode()
    assert "Groceries" in html, "Date filter must show expense from 2026-10-01"


def test_profile_date_filter_excludes_out_of_range_expenses(auth_client):
    """Filter to 2026-10-01 only — 2026-10-12 expenses must not appear."""
    r = auth_client.get("/profile?date_from=2026-10-01&date_to=2026-10-01")
    assert r.status_code == 200
    html = r.data.decode()
    assert "Internet bill" not in html, (
        "Expenses outside the date range must not appear in filtered results"
    )


def test_profile_date_filter_inputs_echo_back_values(auth_client):
    """Applied filter values must be echoed back into the date inputs."""
    r = auth_client.get("/profile?date_from=2026-10-01&date_to=2026-10-31")
    html = r.data.decode()
    assert "2026-10-01" in html, "date_from value must be reflected in the rendered form"
    assert "2026-10-31" in html, "date_to value must be reflected in the rendered form"


# ------------------------------------------------------------------ #
# Tests — date filter: start after end                                #
# ------------------------------------------------------------------ #

def test_profile_start_after_end_flashes_error(auth_client):
    r = auth_client.get("/profile?date_from=2026-10-31&date_to=2026-10-01")
    assert r.status_code == 200, "Invalid date range must return HTTP 200 (re-render)"
    html = r.data.decode()
    assert "Start date must be before end date." in html, (
        "start > end must flash 'Start date must be before end date.'"
    )


def test_profile_start_after_end_still_renders_profile(auth_client):
    """After the date-order error the page must still show user content, not crash."""
    r = auth_client.get("/profile?date_from=2026-12-31&date_to=2026-01-01")
    assert r.status_code == 200, "Page must not crash when start > end"
    html = r.data.decode()
    assert "Demo User" in html, "Profile page must still show user info after date-range error"


def test_profile_start_after_end_clears_filter(auth_client):
    """When dates are invalid the filter should be cleared (all expenses shown)."""
    r = auth_client.get("/profile?date_from=2026-12-31&date_to=2026-01-01")
    html = r.data.decode()
    # With filter cleared all 8 seeded expenses are shown; Groceries is one of them
    assert "Groceries" in html, (
        "After date-range error the filter must be cleared so all expenses are visible"
    )


# ------------------------------------------------------------------ #
# Tests — date filter: malformed date params                         #
# ------------------------------------------------------------------ #

def test_profile_malformed_date_from_ignored(auth_client):
    """A non-date value in date_from must be silently ignored (still returns 200)."""
    r = auth_client.get("/profile?date_from=not-a-date&date_to=2026-10-31")
    assert r.status_code == 200, "Malformed date_from must not crash the page"


def test_profile_malformed_date_to_ignored(auth_client):
    """A non-date value in date_to must be silently ignored (still returns 200)."""
    r = auth_client.get("/profile?date_from=2026-10-01&date_to=garbage")
    assert r.status_code == 200, "Malformed date_to must not crash the page"


def test_profile_both_malformed_dates_ignored(auth_client):
    """Both malformed dates must be ignored — page renders without error."""
    r = auth_client.get("/profile?date_from=abc&date_to=xyz")
    assert r.status_code == 200, "Both malformed date params must be silently ignored"
    html = r.data.decode()
    assert "Demo User" in html, "Profile must render correctly even when both date params are garbage"


def test_profile_malformed_date_does_not_flash_error(auth_client):
    """Silently ignored malformed dates must NOT flash a date-order error."""
    r = auth_client.get("/profile?date_from=bad&date_to=worse")
    html = r.data.decode()
    assert "Start date must be before end date." not in html, (
        "Malformed (unparseable) date params must not produce the date-order flash message"
    )


# ------------------------------------------------------------------ #
# Tests — preset link structure                                       #
# ------------------------------------------------------------------ #

def test_profile_preset_links_contain_date_params(auth_client):
    """Preset links (except All Time) must include date_from and date_to query params."""
    r = auth_client.get("/profile")
    html = r.data.decode()
    assert "date_from=" in html, "Preset filter links must include date_from query params"
    assert "date_to=" in html, "Preset filter links must include date_to query params"


def test_profile_all_time_preset_is_active_by_default(auth_client):
    """With no filter applied, the 'All Time' preset must carry the active CSS class."""
    r = auth_client.get("/profile")
    html = r.data.decode()
    # The active preset anchor contains both the label and the 'active' class close together
    assert "All Time" in html, "'All Time' preset must be present"
    # Find position of "active" class near "All Time"
    idx_all_time = html.find("All Time")
    # Look backwards for "active" within a reasonable window (the <a> tag)
    nearby = html[max(0, idx_all_time - 200):idx_all_time + 20]
    assert "active" in nearby, (
        "The 'All Time' preset link must have the 'active' CSS class when no filter is applied"
    )
