import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "igot_mospi.db")

ALL_DESIGNATIONS_SEED = [
    ('Director General (DG / Apex Level) - ISS', 'Indian Statistical Service (ISS)', 95, 85, 98, 95),
    ('Additional Director General (ADG / HAG) - ISS', 'Indian Statistical Service (ISS)', 94, 85, 95, 92),
    ('Deputy Director General (DDG / SAG) - ISS', 'Indian Statistical Service (ISS)', 92, 88, 92, 90),
    ('Director / Joint Director (JAG) - ISS', 'Indian Statistical Service (ISS)', 92, 90, 88, 85),
    ('Deputy Director (STS) - ISS', 'Indian Statistical Service (ISS)', 90, 92, 85, 82),
    ('Assistant Director (JTS) - ISS', 'Indian Statistical Service (ISS)', 90, 90, 85, 80),
    ('Probationer / Officer Trainee (ISS - NSSTA)', 'Indian Statistical Service (ISS)', 88, 88, 82, 80),
    ('Senior Statistical Officer (SSO / Gazetted)', 'Subordinate Statistical Service (SSS)', 88, 85, 82, 80),
    ('Senior Statistical Officer (SSO / Non-Gazetted)', 'Subordinate Statistical Service (SSS)', 85, 82, 80, 78),
    ('Junior Statistical Officer (JSO)', 'Subordinate Statistical Service (SSS)', 82, 82, 78, 75),
    ('Statistical Assistant / Senior Field Investigator', 'Subordinate Statistical Service (SSS)', 80, 78, 75, 75),
    ('Director of Economics & Statistics (State Head)', 'State DES Statistical Cadre', 92, 85, 95, 92),
    ('Joint / Deputy Director (State DES)', 'State DES Statistical Cadre', 90, 85, 88, 85),
    ('District Statistical Officer (DSO)', 'State DES Statistical Cadre', 85, 82, 82, 82),
    ('Assistant Statistical Officer / Statistical Officer (State)', 'State DES Statistical Cadre', 82, 80, 78, 75),
    ('Statistical Inspector / Research Assistant (DES)', 'State DES Statistical Cadre', 80, 78, 75, 75),
    ('Primary Field Investigator / Enumerator', 'State DES Statistical Cadre', 78, 75, 72, 75)
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(100) DEFAULT 'password123',
        full_name VARCHAR(100) NOT NULL,
        designation VARCHAR(150),
        department VARCHAR(150),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_profiles (
        officer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(100) UNIQUE NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        password VARCHAR(100) DEFAULT 'password123',
        department VARCHAR(150) NOT NULL,
        designation_name VARCHAR(150),
        current_statistical INTEGER DEFAULT 0,
        current_technical INTEGER DEFAULT 0,
        current_governance INTEGER DEFAULT 0,
        current_behavioural INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    # Auto-patch missing columns
    for tbl in ["users", "officer_profiles"]:
        c.execute(f"PRAGMA table_info({tbl});")
        cols = [r["name"] for r in c.fetchall()]
        if "password" not in cols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN password VARCHAR(100) DEFAULT 'password123';")

    c.execute('''
    CREATE TABLE IF NOT EXISTS designation_competency_targets (
        designation_name VARCHAR(150) PRIMARY KEY,
        cadre_name VARCHAR(100) NOT NULL,
        target_statistical INTEGER NOT NULL DEFAULT 85,
        target_technical INTEGER NOT NULL DEFAULT 85,
        target_governance INTEGER NOT NULL DEFAULT 80,
        target_behavioural INTEGER NOT NULL DEFAULT 80
    );''')

    c.executemany("INSERT OR REPLACE INTO designation_competency_targets VALUES (?, ?, ?, ?, ?, ?)", ALL_DESIGNATIONS_SEED)
    conn.commit()
    conn.close()

init_db()

# Flexible Login: accepts credentials from users or officer_profiles with fallback
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    conn = get_db()
    c = conn.cursor()

    # Search officer_profiles first
    c.execute("SELECT full_name, email, password, department, designation_name FROM officer_profiles WHERE LOWER(email) = ?", (email,))
    user = c.fetchone()

    # Fallback to users table
    if not user:
        c.execute("SELECT full_name, email, password, department, designation as designation_name FROM users WHERE LOWER(email) = ?", (email,))
        user = c.fetchone()

    conn.close()

    if not user:
        return jsonify({"status": "error", "message": "No account found with this email. Please register."}), 404

    # If password is set in DB and provided, verify it (otherwise allow seamless transition)
    db_pass = user["password"]
    if db_pass and password and db_pass != password:
        return jsonify({"status": "error", "message": "Incorrect password."}), 401

    return jsonify({
        "status": "success",
        "user": {
            "name": user["full_name"],
            "email": user["email"],
            "department": user["department"],
            "designation": user["designation_name"]
        }
    })

# Registration: writes to both tables and handles duplicates cleanly
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "password123").strip()
    dept = data.get("department", "National Accounts Division").strip()
    desig = data.get("designation", "Junior Statistical Officer (JSO)").strip()

    if not email or not name:
        return jsonify({"status": "error", "message": "Name and Email are required"}), 400

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT email FROM officer_profiles WHERE LOWER(email) = ?", (email,))
    if c.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "This email is already registered!"}), 409

    # Insert into users table
    c.execute("""
        INSERT OR REPLACE INTO users (email, password, full_name, designation, department)
        VALUES (?, ?, ?, ?, ?)
    """, (email, password, name, desig, dept))

    # Insert into officer_profiles table
    c.execute("""
        INSERT OR REPLACE INTO officer_profiles (email, full_name, password, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0)
    """, (email, name, password, dept, desig))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Officer registered successfully"})

# Admin Heatmap: returns all 17 designations
@app.route("/api/admin/heatmap", methods=["GET"])
def get_admin_heatmap():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT 
            t.designation_name,
            t.cadre_name,
            COUNT(o.officer_id) AS enrolled_count,
            t.target_statistical,
            ROUND(COALESCE(AVG(o.current_statistical), 0), 1) AS current_statistical,
            ROUND(MAX(0, t.target_statistical - COALESCE(AVG(o.current_statistical), 0)), 1) AS gap_statistical,
            t.target_technical,
            ROUND(COALESCE(AVG(o.current_technical), 0), 1) AS current_technical,
            ROUND(MAX(0, t.target_technical - COALESCE(AVG(o.current_technical), 0)), 1) AS gap_technical,
            t.target_governance,
            ROUND(COALESCE(AVG(o.current_governance), 0), 1) AS current_governance,
            ROUND(MAX(0, t.target_governance - COALESCE(AVG(o.current_governance), 0)), 1) AS gap_governance,
            t.target_behavioural,
            ROUND(COALESCE(AVG(o.current_behavioural), 0), 1) AS current_behavioural,
            ROUND(MAX(0, t.target_behavioural - COALESCE(AVG(o.current_behavioural), 0)), 1) AS gap_behavioural
        FROM designation_competency_targets t
        LEFT JOIN officer_profiles o ON t.designation_name = o.designation_name
        GROUP BY t.designation_name, t.cadre_name, t.target_statistical, t.target_technical, t.target_governance, t.target_behavioural
        ORDER BY t.cadre_name, t.target_statistical DESC
    """)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"heatmap_data": rows})

@app.route("/api/admin/summary", methods=["GET"])
def get_admin_summary():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM officer_profiles")
    total_officers = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT designation_name) FROM designation_competency_targets")
    total_roles = c.fetchone()[0]

    c.execute("""
        SELECT 
            ROUND(COALESCE(AVG(current_statistical), 0), 1),
            ROUND(COALESCE(AVG(current_technical), 0), 1),
            ROUND(COALESCE(AVG(current_governance), 0), 1),
            ROUND(COALESCE(AVG(current_behavioural), 0), 1)
        FROM officer_profiles
    """)
    avg_row = c.fetchone()
    conn.close()

    return jsonify({
        "total_officers": total_officers,
        "total_designations": total_roles,
        "avg_statistical": avg_row[0] if avg_row else 0,
        "avg_technical": avg_row[1] if avg_row else 0,
        "avg_governance": avg_row[2] if avg_row else 0,
        "avg_behavioural": avg_row[3] if avg_row else 0
    })

if __name__ == "__main__":
    app.run(port=5000, debug=False)