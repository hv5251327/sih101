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
    CREATE TABLE IF NOT EXISTS officer_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(150) NOT NULL,
        email VARCHAR(150) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        designation VARCHAR(150) NOT NULL,
        department VARCHAR(150) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_profiles (
        officer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(150) UNIQUE NOT NULL,
        full_name VARCHAR(150) NOT NULL,
        department VARCHAR(150) NOT NULL,
        designation_name VARCHAR(150),
        current_statistical INTEGER DEFAULT 0,
        current_technical INTEGER DEFAULT 0,
        current_governance INTEGER DEFAULT 0,
        current_behavioural INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS user_progress (
        progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(150) NOT NULL,
        module_id VARCHAR(50) NOT NULL,
        pillar VARCHAR(50) NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(email, module_id)
    );''')

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

@app.route("/api/register", methods=["POST"])
def register():
    try:
        data = request.json or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
        dept = data.get("department", "").strip()
        desig = data.get("designation", "").strip()

        if not email or not name or not password:
            return jsonify({"status": "error", "message": "All fields required"}), 400

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO officer_users (name, email, password, designation, department)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, password, desig, dept))

        c.execute("""
            INSERT INTO officer_profiles (email, full_name, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
            VALUES (?, ?, ?, ?, 0, 0, 0, 0)
            ON CONFLICT(email) DO UPDATE SET full_name=excluded.full_name, department=excluded.department, designation_name=excluded.designation_name
        """, (email, name, dept, desig))

        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if email == "admin@gmail.com" and password == "1234":
            return jsonify({"status": "success", "role": "admin"})

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT name, email, password, designation, department FROM officer_users WHERE LOWER(TRIM(email)) = ?", (email,))
        user = c.fetchone()
        conn.close()

        if not user or user["password"] != password:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

        return jsonify({
            "status": "success",
            "role": "officer",
            "user": {
                "name": user["name"],
                "email": user["email"],
                "designation": user["designation"],
                "department": user["department"]
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/summary", methods=["GET"])
def get_admin_summary():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM officer_users")
    total_officers = c.fetchone()[0]
    conn.close()
    return jsonify({"total_officers": total_officers, "total_designations": 17, "avg_statistical": 0, "avg_technical": 0})

@app.route("/api/admin/heatmap", methods=["GET"])
def get_admin_heatmap():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT designation_name, cadre_name, target_statistical, target_technical, target_governance, target_behavioural FROM designation_competency_targets ORDER BY cadre_name, target_statistical DESC")
    targets = [dict(r) for r in c.fetchall()]

    c.execute("""
        SELECT u.designation, o.current_statistical, o.current_technical, o.current_governance, o.current_behavioural 
        FROM officer_users u 
        LEFT JOIN officer_profiles o ON LOWER(TRIM(u.email)) = LOWER(TRIM(o.email))
    """)
    users = [dict(r) for r in c.fetchall()]
    conn.close()

    heatmap = []
    for t in targets:
        matched = [u for u in users if u['designation'] and (u['designation'].strip().lower() in t['designation_name'].strip().lower() or t['designation_name'].strip().lower() in u['designation'].strip().lower())]
        enrolled = len(matched)
        
        stat_avg = round(sum(u['current_statistical'] or 0 for u in matched) / enrolled, 1) if enrolled > 0 else 0
        tech_avg = round(sum(u['current_technical'] or 0 for u in matched) / enrolled, 1) if enrolled > 0 else 0
        gov_avg = round(sum(u['current_governance'] or 0 for u in matched) / enrolled, 1) if enrolled > 0 else 0
        beh_avg = round(sum(u['current_behavioural'] or 0 for u in matched) / enrolled, 1) if enrolled > 0 else 0

        heatmap.append({
            "designation_name": t["designation_name"],
            "cadre_name": t["cadre_name"],
            "enrolled_count": enrolled,
            "target_statistical": t["target_statistical"],
            "current_statistical": stat_avg,
            "gap_statistical": max(0, round(t["target_statistical"] - stat_avg, 1)),
            "target_technical": t["target_technical"],
            "current_technical": tech_avg,
            "gap_technical": max(0, round(t["target_technical"] - tech_avg, 1)),
            "target_governance": t["target_governance"],
            "current_governance": gov_avg,
            "gap_governance": max(0, round(t["target_governance"] - gov_avg, 1)),
            "target_behavioural": t["target_behavioural"],
            "current_behavioural": beh_avg,
            "gap_behavioural": max(0, round(t["target_behavioural"] - beh_avg, 1))
        })

    return jsonify({"heatmap_data": heatmap})

if __name__ == "__main__":
    app.run(port=5000, debug=False)