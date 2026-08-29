import os
import sqlite3
import json
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

    # Topic Quizzes Table (Stores generated questions per video title/topic)
    c.execute('''
    CREATE TABLE IF NOT EXISTS topic_quizzes (
        quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_title VARCHAR(250) NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option VARCHAR(5) NOT NULL DEFAULT 'a',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    # Officer Completed Modules
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

    conn.commit()
    conn.close()

init_db()

# --- ADMIN API: Store Generated Questions for a Selected Topic ---
@app.route("/api/admin/save-quiz", methods=["POST"])
def save_quiz():
    try:
        data = request.json or {}
        topic_title = data.get("topic_title", "").strip()
        questions = data.get("questions", [])

        if not topic_title or not questions:
            return jsonify({"status": "error", "message": "Topic and questions are required"}), 400

        conn = get_db()
        c = conn.cursor()

        # Delete existing questions for this topic to refresh with new ingestion
        c.execute("DELETE FROM topic_quizzes WHERE LOWER(topic_title) = ?", (topic_title.lower(),))

        for q in questions:
            c.execute("""
                INSERT INTO topic_quizzes (topic_title, question_text, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                topic_title,
                q.get("question", ""),
                q.get("optA", ""),
                q.get("optB", ""),
                q.get("optC", ""),
                q.get("optD", ""),
                q.get("correct", "a")
            ))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": f"{len(questions)} questions saved for topic: {topic_title}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- EMPLOYEE API: Fetch Questions for the Specific Video/Topic ---
@app.route("/api/quiz/get-by-topic", methods=["POST"])
def get_quiz_by_topic():
    try:
        data = request.json or {}
        topic_title = data.get("topic_title", "").strip()

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option
            FROM topic_quizzes
            WHERE LOWER(topic_title) = ?
        """, (topic_title.lower(),))
        rows = c.fetchall()
        conn.close()

        questions = []
        for r in rows:
            questions.append({
                "id": r["quiz_id"],
                "question": r["question_text"],
                "optA": r["option_a"],
                "optB": r["option_b"],
                "optC": r["option_c"],
                "optD": r["option_d"],
                "correct": r["correct_option"]
            })

        return jsonify({"status": "success", "topic": topic_title, "questions": questions})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- PROGRESS API: Complete Course on Passing Assessment ---
@app.route("/api/officer/progress", methods=["POST"])
def complete_progress():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    module_id = data.get("module_id", "")

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE officer_recommendations SET is_completed = 1 WHERE LOWER(officer_email) = ? AND module_id = ?", (email, module_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(port=5000, debug=False)