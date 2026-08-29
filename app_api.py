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
    
    # Create all tables
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        designation TEXT,
        department TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_profiles (
        officer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        department TEXT NOT NULL,
        designation_name TEXT,
        current_statistical INTEGER DEFAULT 0,
        current_technical INTEGER DEFAULT 0,
        current_governance INTEGER DEFAULT 0,
        current_behavioural INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS user_progress (
        progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        module_id TEXT NOT NULL,
        pillar TEXT NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(email, module_id)
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS topic_quizzes (
        quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_title TEXT NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL DEFAULT 'a',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS designation_competency_targets (
        designation_name TEXT PRIMARY KEY,
        cadre_name TEXT NOT NULL,
        target_statistical INTEGER NOT NULL DEFAULT 85,
        target_technical INTEGER NOT NULL DEFAULT 85,
        target_governance INTEGER NOT NULL DEFAULT 80,
        target_behavioural INTEGER NOT NULL DEFAULT 80
    );''')

    c.executemany("INSERT OR REPLACE INTO designation_competency_targets VALUES (?, ?, ?, ?, ?, ?)", ALL_DESIGNATIONS_SEED)
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

init_db()

@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        print(f"Login attempt: {email}")

        # ADMIN LOGIN
        if email == "admin@mospi.gov.in" and password == "admin123":
            print("Admin login successful")
            return jsonify({
                "status": "success", 
                "role": "admin",
                "message": "Admin authenticated"
            })

        # OFFICER LOGIN
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            print(f"User not found: {email}")
            return jsonify({"status": "error", "message": "User not found. Please register first."}), 404
        
        if user["password"] != password:
            print(f"Wrong password for: {email}")
            return jsonify({"status": "error", "message": "Incorrect password."}), 401

        print(f"Officer login successful: {email}")
        return jsonify({
            "status": "success",
            "role": "officer",
            "user": {
                "name": user["full_name"],
                "email": user["email"],
                "designation": user["designation"],
                "department": user["department"]
            }
        })
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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
        c.execute("SELECT email FROM users WHERE LOWER(email) = ?", (email,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Email already registered"}), 409

        c.execute("INSERT INTO users (email, password, full_name, designation, department) VALUES (?, ?, ?, ?, ?)",
                  (email, password, name, desig, dept))
        c.execute("""
            INSERT OR REPLACE INTO officer_profiles (email, full_name, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
            VALUES (?, ?, ?, ?, 0, 0, 0, 0)
        """, (email, name, dept, desig))
        conn.commit()
        conn.close()
        
        print(f"Registration successful: {email}")
        return jsonify({"status": "success", "message": "Registration successful"})
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/officer/progress", methods=["POST"])
def update_officer_progress():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        module_id = data.get("module_id", "")
        pillar = data.get("pillar", "statistical").lower()

        conn = get_db()
        c = conn.cursor()

        c.execute("INSERT OR IGNORE INTO user_progress (email, module_id, pillar) VALUES (?, ?, ?)", (email, module_id, pillar))

        # Recalculate scores
        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = ? AND pillar = 'statistical'", (email,))
        stat_done = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = ? AND pillar = 'technical'", (email,))
        tech_done = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = ? AND pillar = 'governance'", (email,))
        gov_done = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = ? AND pillar = 'behavioural'", (email,))
        beh_done = c.fetchone()[0]

        c.execute("""
            UPDATE officer_profiles 
            SET current_statistical = MIN(100, ? * 100),
                current_technical = MIN(100, ? * 100),
                current_governance = MIN(100, ? * 100),
                current_behavioural = MIN(100, ? * 100)
            WHERE LOWER(email) = ?
        """, (stat_done, tech_done, gov_done, beh_done, email))

        conn.commit()
        conn.close()
        print(f"Progress updated for: {email}")
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Progress update error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/summary", methods=["GET"])
def get_admin_summary():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_officers = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT designation_name) FROM designation_competency_targets")
    total_roles = c.fetchone()[0]
    c.execute("SELECT ROUND(COALESCE(AVG(current_statistical), 0), 1), ROUND(COALESCE(AVG(current_technical), 0), 1) FROM officer_profiles")
    avg_row = c.fetchone()
    conn.close()
    return jsonify({
        "total_officers": total_officers,
        "total_designations": total_roles,
        "avg_statistical": avg_row[0] if avg_row else 0,
        "avg_technical": avg_row[1] if avg_row else 0
    })

@app.route("/api/admin/heatmap", methods=["GET"])
def get_admin_heatmap():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT 
            t.designation_name,
            t.cadre_name,
            COUNT(u.id) AS enrolled_count,
            t.target_statistical,
            ROUND(COALESCE(AVG(o.current_statistical), 0), 1) AS current_statistical,
            t.target_technical,
            ROUND(COALESCE(AVG(o.current_technical), 0), 1) AS current_technical,
            t.target_governance,
            ROUND(COALESCE(AVG(o.current_governance), 0), 1) AS current_governance,
            t.target_behavioural,
            ROUND(COALESCE(AVG(o.current_behavioural), 0), 1) AS current_behavioural
        FROM designation_competency_targets t
        LEFT JOIN users u ON t.designation_name = u.designation
        LEFT JOIN officer_profiles o ON LOWER(u.email) = LOWER(o.email)
        GROUP BY t.designation_name, t.cadre_name
        ORDER BY t.cadre_name, t.target_statistical DESC
    """)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"heatmap_data": rows})

@app.route("/api/admin/save-quiz", methods=["POST"])
def save_quiz():
    try:
        data = request.json or {}
        topic = data.get("topic_title", "").strip()
        questions = data.get("questions", [])
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM topic_quizzes WHERE LOWER(topic_title) = ?", (topic.lower(),))
        for q in questions:
            c.execute("""
                INSERT INTO topic_quizzes (topic_title, question_text, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (topic, q.get("question", ""), q.get("optA", ""), q.get("optB", ""), q.get("optC", ""), q.get("optD", ""), q.get("correct", "a")))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/quiz/get-by-topic", methods=["POST"])
def get_quiz_by_topic():
    try:
        data = request.json or {}
        topic = data.get("topic_title", "").strip()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM topic_quizzes WHERE LOWER(topic_title) = ?", (topic.lower(),))
        rows = c.fetchall()
        conn.close()
        qs = [{"id": r["quiz_id"], "question": r["question_text"], "optA": r["option_a"], "optB": r["option_b"], "optC": r["option_c"], "optD": r["option_d"], "correct": r["correct_option"]} for r in rows]
        return jsonify({"status": "success", "questions": qs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("=" * 70)
    print("MoSPI COMPETENCY PORTAL BACKEND STARTING...")
    print("=" * 70)
    print("Backend API: http://127.0.0.1:5000")
    print("Officer Portal: http://localhost:8080/login.html")
    print("Admin Portal: http://localhost:8080/admin_login.html")
    print("-" * 70)
    print("Admin Credentials: admin@mospi.gov.in / admin123")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)