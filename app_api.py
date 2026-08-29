import os
import sqlite3
import urllib.parse
import requests
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
    CREATE TABLE IF NOT EXISTS designation_competency_targets (
        designation_name VARCHAR(150) PRIMARY KEY,
        cadre_name VARCHAR(100) NOT NULL,
        target_statistical INTEGER NOT NULL DEFAULT 85,
        target_technical INTEGER NOT NULL DEFAULT 85,
        target_governance INTEGER NOT NULL DEFAULT 80,
        target_behavioural INTEGER NOT NULL DEFAULT 80
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_profiles (
        officer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(100) DEFAULT 'password123',
        department VARCHAR(150) NOT NULL,
        designation_name VARCHAR(150),
        current_statistical INTEGER DEFAULT 0,
        current_technical INTEGER DEFAULT 0,
        current_governance INTEGER DEFAULT 0,
        current_behavioural INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    # Automatic Column Migration Check
    c.execute("PRAGMA table_info(officer_profiles);")
    columns = [row["name"] for row in c.fetchall()]
    if "password" not in columns:
        c.execute("ALTER TABLE officer_profiles ADD COLUMN password VARCHAR(100) DEFAULT 'password123';")

    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_recommendations (
        rec_id INTEGER PRIMARY KEY AUTOINCREMENT,
        officer_email VARCHAR(100) NOT NULL,
        designation_name VARCHAR(150) NOT NULL,
        module_id VARCHAR(50) NOT NULL,
        module_title VARCHAR(250) NOT NULL,
        pillar VARCHAR(50) NOT NULL,
        embed_url TEXT NOT NULL,
        is_completed INTEGER DEFAULT 0,
        recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(officer_email, module_id)
    );''')

    c.executemany("INSERT OR REPLACE INTO designation_competency_targets VALUES (?, ?, ?, ?, ?, ?)", ALL_DESIGNATIONS_SEED)
    conn.commit()
    conn.close()

init_db()

VIDEO_CATALOG = {
    "ISS": [
        {"id": "iss-stat-1", "title": "SNA 2008 & 2025: National Accounts Compilation", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-stat-2", "title": "Large-Scale Survey Design & Probability Weight Estimation", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-tech-1", "title": "Advanced Python & SQL for Official Sample Imputation", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-gov-1", "title": "DPDP Act 2023 & National Data Governance Architecture", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-beh-1", "title": "Apex Statistical Leadership & Policy Negotiation", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"}
    ],
    "SSS": [
        {"id": "sss-stat-1", "title": "PLFS & ASUSE Schedule Filling & Validation Guidelines", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-stat-2", "title": "Consumer Price Index (CPI) Rural/Urban Quotation Protocols", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-tech-1", "title": "CAPI Tablet Operations & Real-Time Data Synchronization", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-tech-2", "title": "Bhuvan GIS Ground Truthing & Urban Frame Survey Mapping", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-gov-1", "title": "Field Data Confidentiality & Respondent Privacy Protocols", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-beh-1", "title": "Enumerator Team Supervision & Effective Public Interviewing", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"}
    ],
    "DES": [
        {"id": "des-stat-1", "title": "Gross State Domestic Product (GSDP) & State Income Estimation", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-stat-2", "title": "Crop Estimation Surveys (EARAS) & State Agricultural Statistics", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-tech-1", "title": "State Statistical Open Portals & GIS District Tabulation", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-gov-1", "title": "Civil Registration System (CRS) & State-Centre Data Protocols", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-beh-1", "title": "District Administration Liaison & Field Survey Coordination", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"}
    ]
}

def get_cadre(desig):
    if any(k in desig for k in ["ISS", "Director General", "Director (", "Deputy Director", "Assistant Director"]):
        return "ISS"
    if any(k in desig for k in ["DES", "State", "District Statistical"]):
        return "DES"
    return "SSS"

@app.route("/api/register", methods=["POST"])
def register_officer():
    try:
        data = request.json or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
        dept = data.get("department", "").strip()
        desig = data.get("designation", "").strip()

        if not email or not name or not password:
            return jsonify({"status": "error", "message": "All fields including password are required"}), 400

        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT email FROM officer_profiles WHERE LOWER(email) = ?", (email,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Officer with this email is already registered!"}), 409

        c.execute("""
            INSERT INTO officer_profiles (full_name, email, password, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0)
        """, (name, email, password, dept, desig))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Registration successful"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def login_officer():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"status": "error", "message": "Email and password are required"}), 400

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT full_name, email, password, department, designation_name FROM officer_profiles WHERE LOWER(email) = ?", (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            return jsonify({"status": "error", "message": "No account found with this email. Please register first."}), 404

        if user["password"] != password:
            return jsonify({"status": "error", "message": "Incorrect password. Please try again."}), 401

        return jsonify({
            "status": "success",
            "user": {
                "name": user["full_name"],
                "email": user["email"],
                "department": user["department"],
                "designation": user["designation_name"]
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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

@app.route("/api/officer/recommendations", methods=["POST"])
def get_recommendations():
    data = request.json or {}
    email = data.get("email", "officer@gov.in")
    designation = data.get("designation", "Junior Statistical Officer (JSO)")
    cadre = get_cadre(designation)
    mods = VIDEO_CATALOG.get(cadre, VIDEO_CATALOG["SSS"])

    conn = get_db()
    c = conn.cursor()
    for m in mods:
        c.execute("""
            INSERT OR IGNORE INTO officer_recommendations 
            (officer_email, designation_name, module_id, module_title, pillar, embed_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, designation, m["id"], m["title"], m["pillar"], m["embedUrl"]))
    conn.commit()

    c.execute("SELECT module_id, is_completed FROM officer_recommendations WHERE officer_email = ?", (email,))
    done_map = {row[0]: bool(row[1]) for row in c.fetchall()}
    conn.close()

    result = []
    for m in mods:
        item = dict(m)
        item["is_completed"] = done_map.get(m["id"], False)
        result.append(item)
    return jsonify({"cadre": cadre, "modules": result})

@app.route("/api/officer/progress", methods=["POST"])
def update_progress():
    data = request.json or {}
    email = data.get("email", "officer@gov.in")
    module_id = data.get("module_id", "")
    pillar = data.get("pillar", "statistical")

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE officer_recommendations SET is_completed = 1 WHERE officer_email = ? AND module_id = ?", (email, module_id))
    
    c.execute("SELECT COUNT(*) FROM officer_recommendations WHERE officer_email = ? AND pillar = ?", (email, pillar))
    total = c.fetchone()[0] or 1
    c.execute("SELECT COUNT(*) FROM officer_recommendations WHERE officer_email = ? AND pillar = ? AND is_completed = 1", (email, pillar))
    completed = c.fetchone()[0]
    percentage = int(round((completed / total) * 100))

    col_map = {"statistical": "current_statistical", "technical": "current_technical", "governance": "current_governance", "behavioural": "current_behavioural"}
    c.execute(f"UPDATE officer_profiles SET {col_map.get(pillar, 'current_statistical')} = ? WHERE email = ?", (percentage, email))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "pillar": pillar, "new_percentage": percentage})

if __name__ == "__main__":
    app.run(port=5000, debug=False)