from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["DATABASE"] = Path(app.root_path) / "helpdesk.db"

STATUSES = ("Open", "In Progress", "Waiting on Employee", "Resolved")
PRIORITIES = ("Low", "Medium", "High", "Critical")
CATEGORIES = ("Hardware", "Software", "Network", "Access & Accounts", "Security", "Other")
TECHNICIANS = ("Unassigned", "Maya Chen", "Jordan Williams", "Alex Rivera")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS tickets (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          description TEXT NOT NULL,
          category TEXT NOT NULL,
          priority TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Open',
          requester_name TEXT NOT NULL,
          requester_email TEXT NOT NULL,
          assignee TEXT NOT NULL DEFAULT 'Unassigned',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ticket_id INTEGER NOT NULL,
          author TEXT NOT NULL,
          body TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        );
        """
    )
    if db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        examples = [
            ("VPN connection fails", "I cannot connect to the company VPN from home. It says authentication failed.", "Network", "High", "In Progress", "Jason Coc", "cocjason01@northstar.local", "Jadiel Pop"),
            ("Request access to Finance Drive", "Please add me to the Finance Q3 planning folder.", "Access & Accounts", "Medium", "Open", "Noah Davis", "noah@northstar.local", "Unassigned"),
            ("Laptop battery draining quickly", "My laptop drops from 100% to 20% within an hour while unplugged.", "Hardware", "Low", "Resolved", "Emma Wilson", "emma@northstar.local", "Jordan Williams"),
        ]
        for title, description, category, priority, status, name, email, assignee in examples:
            db.execute("INSERT INTO tickets (title,description,category,priority,status,requester_name,requester_email,assignee,created_at,updated_at,resolved_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (title, description, category, priority, status, name, email, assignee, now, now, now if status == "Resolved" else None))
        db.execute("INSERT INTO notes (ticket_id,author,body,created_at) VALUES (1,?,?,?)", ("Maya Chen", "Checked VPN gateway logs. Resetting the remote access profile.", now))
    db.commit()


@app.before_request
def ensure_database():
    init_db()


def ticket_or_404(ticket_id):
    ticket = get_db().execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not ticket:
        abort(404)
    return ticket


@app.route("/")
def index():
    db = get_db()
    counts = {row["status"]: row["total"] for row in db.execute("SELECT status, COUNT(*) total FROM tickets GROUP BY status")}
    recent = db.execute("SELECT * FROM tickets ORDER BY datetime(updated_at) DESC, id DESC LIMIT 5").fetchall()
    return render_template("index.html", counts=counts, recent=recent)


@app.route("/tickets")
def tickets():
    filters = {key: request.args.get(key, "") for key in ("status", "priority", "category", "q")}
    sql, params = "SELECT * FROM tickets WHERE 1=1", []
    for key in ("status", "priority", "category"):
        if filters[key]:
            sql += f" AND {key} = ?"
            params.append(filters[key])
    if filters["q"]:
        sql += " AND (title LIKE ? OR requester_name LIKE ? OR requester_email LIKE ?)"
        params.extend([f"%{filters['q']}%"] * 3)
    sql += " ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, datetime(updated_at) DESC"
    rows = get_db().execute(sql, params).fetchall()
    return render_template("tickets.html", tickets=rows, filters=filters)


@app.route("/tickets/new", methods=("GET", "POST"))
def new_ticket():
    if request.method == "POST":
        data = {key: request.form.get(key, "").strip() for key in ("title", "description", "category", "priority", "requester_name", "requester_email")}
        if not all(data.values()) or data["category"] not in CATEGORIES or data["priority"] not in PRIORITIES:
            flash("Please complete every field with a valid category and priority.", "error")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            cur = get_db().execute("INSERT INTO tickets (title,description,category,priority,requester_name,requester_email,created_at,updated_at) VALUES (:title,:description,:category,:priority,:requester_name,:requester_email,:created_at,:updated_at)", {**data, "created_at": now, "updated_at": now})
            get_db().commit()
            flash(f"Ticket #{cur.lastrowid} was submitted to IT.", "success")
            return redirect(url_for("ticket_detail", ticket_id=cur.lastrowid))
    return render_template("new_ticket.html")


@app.route("/tickets/<int:ticket_id>")
def ticket_detail(ticket_id):
    ticket = ticket_or_404(ticket_id)
    notes = get_db().execute("SELECT * FROM notes WHERE ticket_id = ? ORDER BY id", (ticket_id,)).fetchall()
    return render_template("ticket_detail.html", ticket=ticket, notes=notes)


@app.route("/tickets/<int:ticket_id>/manage", methods=("POST",))
def manage_ticket(ticket_id):
    ticket_or_404(ticket_id)
    status, assignee, note = request.form.get("status"), request.form.get("assignee"), request.form.get("note", "").strip()
    if status not in STATUSES or assignee not in TECHNICIANS:
        abort(400)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    resolved_at = now if status == "Resolved" else None
    db = get_db()
    db.execute("UPDATE tickets SET status=?, assignee=?, updated_at=?, resolved_at=? WHERE id=?", (status, assignee, now, resolved_at, ticket_id))
    if note:
        db.execute("INSERT INTO notes (ticket_id,author,body,created_at) VALUES (?,?,?,?)", (ticket_id, "IT Support", note, now))
    db.commit()
    flash("Ticket updated.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


if __name__ == "__main__":
    app.run(debug=True)
