"""Meridian Expenses - assessment remediation example, restricted to localhost.
Read README.md before running. Not production-hardened or independently audited.
"""
import csv
import io
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import (Flask, abort, g, make_response, redirect, render_template,
                   request, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("MERIDIAN_SECRET_KEY")
if not app.secret_key or len(app.secret_key) < 32:
    raise RuntimeError("Set MERIDIAN_SECRET_KEY to at least 32 unpredictable characters.")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("MERIDIAN_HTTPS") == "1")
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "expenses.db")
RECEIPTS = os.path.join(BASE, "receipts")


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close(_exc):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def current_user():
    if "current_user" not in g:
        uid = session.get("uid")
        g.current_user = (db().execute(
            "SELECT id, name, role FROM users WHERE id = ?", (uid,)).fetchone()
            if isinstance(uid, int) else None)
    return g.current_user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user()["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def csrf_context():
    return {"csrf_token": csrf_token}


@app.before_request
def check_csrf():
    if request.method == "POST":
        supplied = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            abort(403)


@app.route("/")
@login_required
def index():
    rows = db().execute(
        "SELECT * FROM claims WHERE user_id = ? ORDER BY id DESC",
        (current_user()["id"],)).fetchall()
    return render_template("index.html", claims=rows, user=current_user()["name"])


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = db().execute(
            "SELECT id, password FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["uid"] = user["id"]
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/claim/<int:cid>")
@login_required
def claim(cid):
    user = current_user()
    if user["role"] in ("admin", "finance"):
        row = db().execute("SELECT * FROM claims WHERE id = ?", (cid,)).fetchone()
    else:
        row = db().execute(
            "SELECT * FROM claims WHERE id = ? AND user_id = ?",
            (cid, user["id"])).fetchone()
    if row is None:
        abort(404)
    return render_template("claim.html", c=row)


@app.route("/claim/new", methods=["POST"])
@login_required
def new_claim():
    merchant = request.form.get("merchant", "").strip()
    note = request.form.get("note", "")
    try:
        amount = float(request.form.get("amount", ""))
    except (ValueError, TypeError):
        abort(400)
    if not (1 <= len(merchant) <= 120 and 0 < amount <= 100000 and
            len(note) <= 2000 and amount == amount and amount != float("inf")):
        abort(400)
    created_at = datetime.now(timezone.utc).date().isoformat()
    db().execute(
        "INSERT INTO claims (user_id, merchant, amount, note, status, created_at) "
        "VALUES (?, ?, ?, ?, 'pending', ?)",
        (current_user()["id"], merchant, amount, note, created_at))
    db().commit()
    return redirect(url_for("index"))


@app.route("/receipt")
@login_required
def receipt():
    # User input is a receipt identifier, never an arbitrary filesystem path.
    matched = re.fullmatch(r"claim-([1-9][0-9]*)\.txt", request.args.get("f", ""))
    if not matched:
        abort(400)
    cid = int(matched.group(1))
    user = current_user()
    if user["role"] in ("admin", "finance"):
        row = db().execute("SELECT 1 FROM claims WHERE id = ?", (cid,)).fetchone()
    else:
        row = db().execute("SELECT 1 FROM claims WHERE id = ? AND user_id = ?",
                           (cid, user["id"])).fetchone()
    if row is None:
        abort(404)
    return send_from_directory(RECEIPTS, f"claim-{cid}.txt", mimetype="text/plain")


def csv_cell(value):
    """Prevent spreadsheet-formula execution on export without changing database data."""
    string = "" if value is None else str(value)
    if string.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + string
    return string


@app.route("/export")
@roles_required("finance", "admin")
def export():
    month = request.args.get("month", datetime.now(timezone.utc).strftime("%Y-%m"))
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
        abort(400)
    rows = db().execute(
        "SELECT id, user_id, merchant, amount, note, status, created_at "
        "FROM claims WHERE substr(created_at, 1, 7) = ? ORDER BY id", (month,)
    ).fetchall()
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(("id", "user_id", "merchant", "amount", "note", "status", "created_at"))
    for row in rows:
        writer.writerow([csv_cell(field) for field in row])
    response = make_response(stream.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="expenses-{month}.csv"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/prefs", methods=["POST"])
@login_required
def prefs():
    try:
        data = json.loads(request.form.get("prefs", "{}"))
    except json.JSONDecodeError:
        abort(400)
    if not isinstance(data, dict) or set(data) - {"theme", "page_size"}:
        abort(400)
    theme = data.get("theme", "light")
    size = data.get("page_size", 20)
    if theme not in ("light", "dark") or type(size) is not int or not 5 <= size <= 100:
        abort(400)
    session["prefs"] = {"theme": theme, "page_size": size}
    return redirect(url_for("index"))


@app.route("/admin/users")
@roles_required("admin")
def admin_users():
    rows = db().execute("SELECT id, username, name, role FROM users").fetchall()
    return render_template("admin.html", users=rows)


# The /debug/config route is deliberately removed; credentials and runtime
# configuration must not be provided through an HTTP endpoint.

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
