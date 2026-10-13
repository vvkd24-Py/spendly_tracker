from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    dt = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": dt.strftime("%B %Y"),
    }


def get_summary_stats(user_id, date_from=None, date_to=None):
    date_clause = ""
    date_params = []
    if date_from and date_to:
        date_clause = " AND date BETWEEN ? AND ?"
        date_params = [date_from, date_to]

    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount), 0) "
        "FROM expenses WHERE user_id = ?" + date_clause,
        [user_id] + date_params,
    ).fetchone()
    count = row[0]
    total = row[1]

    if count == 0:
        conn.close()
        return {"total_spent": "0.00", "transaction_count": 0, "top_category": "—"}

    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ?" + date_clause +
        " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        [user_id] + date_params,
    ).fetchone()
    conn.close()

    return {
        "total_spent": "%.2f" % total,
        "transaction_count": count,
        "top_category": top["category"],
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    date_clause = ""
    date_params = []
    if date_from and date_to:
        date_clause = " AND date BETWEEN ? AND ?"
        date_params = [date_from, date_to]

    conn = get_db()
    rows = conn.execute(
        "SELECT id, date, description, category, amount "
        "FROM expenses WHERE user_id = ?" + date_clause +
        " ORDER BY date DESC, id DESC LIMIT ?",
        [user_id] + date_params + [limit],
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, amount, category, date, description "
        "FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_expense(expense_id, user_id, amount, category, date, description):
    conn = get_db()
    conn.execute(
        "UPDATE expenses SET amount=?, category=?, date=?, description=? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description, expense_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    conn.commit()
    conn.close()


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id


def get_category_breakdown(user_id, date_from=None, date_to=None):
    date_clause = ""
    date_params = []
    if date_from and date_to:
        date_clause = " AND date BETWEEN ? AND ?"
        date_params = [date_from, date_to]

    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS amount "
        "FROM expenses WHERE user_id = ?" + date_clause +
        " GROUP BY category ORDER BY amount DESC",
        [user_id] + date_params,
    ).fetchall()
    conn.close()

    if not rows:
        return []

    items = [{"name": row["category"], "amount": row["amount"]} for row in rows]
    total = sum(item["amount"] for item in items)

    pcts = [round(item["amount"] / total * 100) for item in items]
    pcts[0] += 100 - sum(pcts)

    for item, pct in zip(items, pcts):
        item["pct"] = pct

    return items
