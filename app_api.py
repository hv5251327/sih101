import os
import sqlite3
import requests
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
    
    # 1. users table (Authentication)
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        designation VARCHAR(150),
        department VARCHAR(150),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    # 2. officer_profiles table (Competency Tracking)
    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_profiles (
        officer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(100) UNIQUE NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        department VARCHAR(150) NOT NULL,
        designation_name VARCHAR(150),
        current_statistical INTEGER DEFAULT 0,
        current_technical INTEGER DEFAULT 0,
        current_governance INTEGER DEFAULT 0,
        current_behavioural INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (email) REFERENCES users(email)
    );''')

    # 3. designation_competency_targets table
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

# --- Registration: Writes to both `users` and `officer_profiles` ---
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
            return jsonify({"status": "error", "message": "All fields are required"}), 400

        conn = get_db()
        c = conn.cursor()

        # Check existing user
        c.execute("SELECT email FROM users WHERE LOWER(email) = ?", (email,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Email is already registered!"}), 409

        # Insert into users
        c.execute("INSERT INTO users (email, password, full_name, designation, department) VALUES (?, ?, ?, ?, ?)",
                  (email, password, name, desig, dept))

        # Insert into officer_profiles
        c.execute("""
            INSERT INTO officer_profiles (email, full_name, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
            VALUES (?, ?, ?, ?, 0, 0, 0, 0)
        """, (email, name, dept, desig))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Registered successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Login: Verifies credentials from `users` and fetches profile ---
@app.route("/api/login", methods=["POST"])
def login_officer():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT u.email, u.password, u.full_name, u.department, u.designation
            FROM users u
            WHERE LOWER(u.email) = ?
        """, (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            return jsonify({"status": "error", "message": "Account not found. Please register first."}), 404

        if user["password"] != password:
            return jsonify({"status": "error", "message": "Incorrect password. Please try again."}), 401

        return jsonify({
            "status": "success",
            "user": {
                "name": user["full_name"],
                "email": user["email"],
                "department": user["department"],
                "designation": user["designation"]
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Admin Heatmap: Aggregates across targets and officer_profiles ---
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

if __name__ == "__main__":
    app.run(port=5000, debug=False)