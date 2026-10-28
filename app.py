import calendar
import sqlite3
from datetime import date, datetime

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db
from database.queries import (
    delete_expense as _delete_expense,
    get_category_breakdown,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    insert_expense,
    update_expense,
)
from werkzeug.security import check_password_hash

import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "spendly-dev-secret-key")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm_password]):
            flash("All fields are required.")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return render_template("register.html")

        flash("Account created! Please sign in.")
        return redirect(url_for("login"))

    abort(405)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.")
            return render_template("login.html")

        session["user_id"] = user["id"]
        return redirect(url_for("landing"))

    abort(405)


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


def _subtract_months(d, n):
    month, year = d.month - n, d.year
    while month <= 0:
        month += 12
        year -= 1
    return d.replace(year=year, month=month,
                     day=min(d.day, calendar.monthrange(year, month)[1]))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # --- Date filter parsing and validation ---
    raw_from = request.args.get("date_from", "").strip()
    raw_to   = request.args.get("date_to",   "").strip()

    date_from = date_to = None
    try:
        if raw_from:
            datetime.strptime(raw_from, "%Y-%m-%d")
            date_from = raw_from
    except ValueError:
        pass
    try:
        if raw_to:
            datetime.strptime(raw_to, "%Y-%m-%d")
            date_to = raw_to
    except ValueError:
        pass

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = None

    # --- Preset date ranges ---
    today          = date.today()
    today_s        = today.isoformat()
    this_month_s   = today.replace(day=1).isoformat()
    three_months_s = _subtract_months(today, 3).isoformat()
    six_months_s   = _subtract_months(today, 6).isoformat()

    presets = [
        {
            "label": "This Month",
            "url": url_for("profile", date_from=this_month_s, date_to=today_s),
            "active": date_from == this_month_s and date_to == today_s,
        },
        {
            "label": "Last 3 Months",
            "url": url_for("profile", date_from=three_months_s, date_to=today_s),
            "active": date_from == three_months_s and date_to == today_s,
        },
        {
            "label": "Last 6 Months",
            "url": url_for("profile", date_from=six_months_s, date_to=today_s),
            "active": date_from == six_months_s and date_to == today_s,
        },
        {
            "label": "All Time",
            "url": url_for("profile"),
            "active": date_from is None and date_to is None,
        },
    ]

    # --- User data ---
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    parts = user["name"].split()
    user["initials"] = "".join(p[0].upper() for p in parts[:2])

    stats              = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    expenses           = get_recent_transactions(user_id, limit=10, date_from=date_from, date_to=date_to)
    category_breakdown = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        expenses=expenses,
        category_breakdown=category_breakdown,
        date_from=date_from,
        date_to=date_to,
        presets=presets,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            today=date.today().isoformat(),
            form={},
        )

    if request.method == "POST":
        raw_amount = request.form.get("amount", "").strip()
        category   = request.form.get("category", "").strip()
        raw_date   = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip() or None

        form = {
            "amount": raw_amount,
            "category": category,
            "date": raw_date,
            "description": description or "",
        }

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number greater than 0.")
            return render_template("add_expense.html", categories=CATEGORIES,
                                   today=date.today().isoformat(), form=form)

        if category not in CATEGORIES:
            flash("Please select a valid category.")
            return render_template("add_expense.html", categories=CATEGORIES,
                                   today=date.today().isoformat(), form=form)

        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            flash("Please enter a valid date.")
            return render_template("add_expense.html", categories=CATEGORIES,
                                   today=date.today().isoformat(), form=form)

        insert_expense(session["user_id"], amount, category, raw_date, description)
        return redirect(url_for("profile"))

    abort(405)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=CATEGORIES,
        )

    if request.method == "POST":
        raw_amount  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        raw_date    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip() or None

        form = {
            "id":          expense["id"],
            "amount":      raw_amount,
            "category":    category,
            "date":        raw_date,
            "description": description or "",
        }

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number greater than 0.")
            return render_template("edit_expense.html", expense=form,
                                   categories=CATEGORIES)

        if category not in CATEGORIES:
            flash("Please select a valid category.")
            return render_template("edit_expense.html", expense=form,
                                   categories=CATEGORIES)

        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            flash("Please enter a valid date.")
            return render_template("edit_expense.html", expense=form,
                                   categories=CATEGORIES)

        update_expense(id, session["user_id"], amount, category, raw_date, description)
        return redirect(url_for("profile"))

    abort(405)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    _delete_expense(id, session["user_id"])
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
