import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# Replace with your actual Supabase PostgreSQL connection URI string
# (Found in Supabase Dashboard -> Project Settings -> Database -> Connection string -> URI)
SUPABASE_DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:your_password@db.your-project.supabase.co:5432/postgres")

def get_db():
    conn = psycopg2.connect(SUPABASE_DB_URL, cursor_factory=RealDictCursor)
    return conn

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
        
        # Insert into Supabase public.users table using PostgreSQL %s syntax
        c.execute("""
            INSERT INTO users (name, email, hashed_password, designation, department)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE 
            SET name = EXCLUDED.name, 
                hashed_password = EXCLUDED.hashed_password, 
                designation = EXCLUDED.designation, 
                department = EXCLUDED.department
        """, (name, email, password, desig, dept))

        # Insert or update officer profiles for live heatmap sync
        c.execute("""
            INSERT INTO officer_profiles (email, full_name, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
            VALUES (%s, %s, %s, %s, 0, 0, 0, 0)
            ON CONFLICT (email) DO UPDATE 
            SET full_name = EXCLUDED.full_name, 
                department = EXCLUDED.department, 
                designation_name = EXCLUDED.designation_name
        """, (email, name, dept, desig))

        conn.commit()
        c.close()
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
        c.execute("SELECT name, email, hashed_password, designation, department FROM users WHERE LOWER(TRIM(email)) = %s", (email,))
        user = c.fetchone()
        c.close()
        conn.close()

        if not user or user["hashed_password"] != password:
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

@app.route("/api/officer/progress", methods=["POST"])
def update_officer_progress():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        module_id = data.get("module_id", "")
        pillar = data.get("pillar", "statistical").lower()

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO user_progress (email, module_id, pillar) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (email, module_id) DO NOTHING
        """, (email, module_id, pillar))

        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = %s AND pillar = 'statistical'", (email,))
        stat_done = c.fetchone()['count']
        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = %s AND pillar = 'technical'", (email,))
        tech_done = c.fetchone()['count']
        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = %s AND pillar = 'governance'", (email,))
        gov_done = c.fetchone()['count']
        c.execute("SELECT COUNT(*) FROM user_progress WHERE LOWER(email) = %s AND pillar = 'behavioural'", (email,))
        beh_done = c.fetchone()['count']

        c.execute("""
            UPDATE officer_profiles
            SET current_statistical = LEAST(100, %s * 100),
                current_technical = LEAST(100, %s * 100),
                current_governance = LEAST(100, %s * 100),
                current_behavioural = LEAST(100, %s * 100)
            WHERE LOWER(email) = %s
        """, (stat_done, tech_done, gov_done, beh_done, email))

        conn.commit()
        c.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/summary", methods=["GET"])
def get_admin_summary():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_officers = c.fetchone()['count']
    c.execute("""
        SELECT
            ROUND(COALESCE(AVG(current_statistical), 0), 1),
            ROUND(COALESCE(AVG(current_technical), 0), 1)
        FROM officer_profiles
    """)
    avg_row = c.fetchone()
    c.close()
    conn.close()
    return jsonify({
        "total_officers": total_officers,
        "total_designations": 17,
        "avg_statistical": list(avg_row.values())[0] if avg_row else 0,
        "avg_technical": list(avg_row.values())[1] if avg_row else 0
    })

@app.route("/api/admin/heatmap", methods=["GET"])
def get_admin_heatmap():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT designation_name, cadre_name, target_statistical, target_technical, target_governance, target_behavioural FROM designation_competency_targets ORDER BY cadre_name, target_statistical DESC")
    targets = [dict(r) for r in c.fetchall()]

    c.execute("""
        SELECT u.designation, o.current_statistical, o.current_technical, o.current_governance, o.current_behavioural 
        FROM users u 
        LEFT JOIN officer_profiles o ON LOWER(TRIM(u.email)) = LOWER(TRIM(o.email))
    """)
    users = [dict(r) for r in c.fetchall()]
    c.close()
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

@app.route("/api/admin/save-quiz", methods=["POST"])
def save_quiz():
    try:
        data = request.json or {}
        topic = data.get("topic_title", "").strip()
        questions = data.get("questions", [])
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM topic_quizzes WHERE LOWER(topic_title) = LOWER(%s)", (topic,))
        for q in questions:
            c.execute("""
                INSERT INTO topic_quizzes (topic_title, question_text, option_a, option_b, option_c, option_d, correct_option)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (topic, q.get("question", ""), q.get("optA", ""), q.get("optB", ""), q.get("optC", ""), q.get("optD", ""), q.get("correct", "a")))
        conn.commit()
        c.close()
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
        c.execute("SELECT quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option FROM topic_quizzes WHERE LOWER(topic_title) = LOWER(%s)", (topic,))
        rows = c.fetchall()
        c.close()
        conn.close()
        qs = [{"id": r["quiz_id"], "question": r["question_text"], "optA": r["option_a"], "optB": r["option_b"], "optC": r["option_c"], "optD": r["option_d"], "correct": r["correct_option"]} for r in rows]
        return jsonify({"status": "success", "questions": qs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=False)