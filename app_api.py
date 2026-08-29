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

@app.route("/api/officer/progress", methods=["POST"])
def update_progress():
    data = request.json or {}
    email = data.get("email", "officer@gov.in")
    pillar = data.get("pillar", "statistical")
    points = int(data.get("points", 20))

    col_map = {
        "statistical": "current_statistical",
        "technical": "current_technical",
        "governance": "current_governance",
        "behavioural": "current_behavioural"
    }
    
    col = col_map.get(pillar, "current_statistical")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE officer_profiles 
        SET {col} = MIN(100, {col} + ?) 
        WHERE email = ?
    """, (points, email))
    conn.commit()

    cursor.execute("SELECT * FROM officer_individual_competency_view WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    return jsonify({"status": "success", "updated_pillar": pillar, "points_added": points})

if __name__ == "__main__":
    app.run(port=5000, debug=False)