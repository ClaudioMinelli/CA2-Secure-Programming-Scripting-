"""Reset the laboratory database (destroys data). Synthetic examples only."""
import os
import sqlite3
from werkzeug.security import generate_password_hash

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")
if os.path.exists(DB):
    os.remove(DB)
c = sqlite3.connect(DB)
c.executescript("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL
);
CREATE TABLE claims (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, merchant TEXT NOT NULL,
    amount REAL NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
""")
users = [("jdoe", "password1", "Jane Doe", "staff"),
         ("rsmith", "letmein", "Rob Smith", "staff"),
         ("achen", "Summer2026", "Ada Chen", "finance"),
         ("admin", "admin", "System Admin", "admin")]
for username, pw, name, role in users:
    c.execute("INSERT INTO users(username,password,name,role) VALUES (?,?,?,?)",
              (username, generate_password_hash(pw, method="scrypt"), name, role))
claims = [(1, "Dublin Coach", 24.50, "Client visit", "approved", "2026-09-03"),
          (1, "Aer Lingus", 310.00, "Conference travel", "pending", "2026-09-08"),
          (2, "Tesco", 18.20, "Team lunch", "approved", "2026-09-09"),
          (3, "Hotel Riu", 480.00, "Offsite accommodation", "pending", "2026-09-14"),
          (4, "Amazon", 129.99, "Spare laptop charger", "approved", "2026-09-18")]
for claim in claims:
    c.execute("""INSERT INTO claims(user_id,merchant,amount,note,status,created_at)
                 VALUES(?,?,?,?,?,?)""", claim)
c.commit()
c.close()
receipts = os.path.join(os.path.dirname(DB), "receipts")
os.makedirs(receipts, exist_ok=True)
for i in range(1, 6):
    with open(os.path.join(receipts, f"claim-{i}.txt"), "w", encoding="utf-8") as f:
        f.write(f"Meridian Expenses - receipt for claim {i}\nSynthetic laboratory data.\n")
print("seeded:", DB)
