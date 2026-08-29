import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "igot_mospi.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Matches Supabase schema exactly: name, hashed_password
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(150) NOT NULL,
        email VARCHAR(150) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        designation VARCHAR(150),
        department VARCHAR(150),
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
        c.execute("SELECT email FROM users WHERE LOWER(email) = ?", (email,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Email already registered"}), 409

        # Storing with correct column names: name, hashed_password
        c.execute("INSERT INTO users (name, email, hashed_password, designation, department) VALUES (?, ?, ?, ?, ?)",
                  (name, email, password, desig, dept))
        c.execute("""
            INSERT INTO officer_profiles (email, full_name, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
            VALUES (?, ?, ?, ?, 0, 0, 0, 0)
            ON CONFLICT(email) DO UPDATE SET full_name=excluded.full_name, department=excluded.department, designation_name=excluded.designation_name
        """, (email, name, dept, desig))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "User registered successfully"})
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
        c.execute("SELECT name, email, hashed_password, designation, department FROM users WHERE LOWER(email) = ?", (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            return jsonify({"status": "error", "message": "Account not found"}), 404
        if user["hashed_password"] != password:
            return jsonify({"status": "error", "message": "Incorrect password"}), 401

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
    c.execute("SELECT COUNT(*) FROM users")
    total_officers = c.fetchone()[0]
    conn.close()
    return jsonify({"total_officers": total_officers, "total_designations": 17, "avg_statistical": 0, "avg_technical": 0})

if __name__ == "__main__":
    app.run(port=5000, debug=False)