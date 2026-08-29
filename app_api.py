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
    new_percentage = int(data.get("percentage", 0))

    col_map = {
        "statistical": "current_statistical",
        "technical": "current_technical",
        "governance": "current_governance",
        "behavioural": "current_behavioural"
    }
    col = col_map.get(pillar, "current_statistical")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE officer_profiles SET {col} = ? WHERE email = ?", (new_percentage, email))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "updated_pillar": pillar, "new_percentage": new_percentage})

@app.route("/api/chatbot", methods=["POST"])
def chatbot_reply():
    data = request.json or {}
    msg = data.get("message", "").lower()
    
    if "pillar" in msg or "competency" in msg:
        reply = "MoSPI's framework assesses 4 pillars: Statistical Frameworks, Technical Tools, Digital Governance, and Behavioural/Managerial Skills."
    elif "certificate" in msg or "upload" in msg:
        reply = "Uploading your certificate marks that specific video module as completed, dynamically updating that pillar's percentage based on total completed videos."
    elif "gap" in msg:
        reply = "Your competency gap is the difference between the mandated NSSTA target for your designation and your verified completed modules."
    else:
        reply = f"I am your MoSPI AI Learning Assistant. I can help guide your progress across the 4 pillars and recommend relevant NSSTA / iGOT courses."

    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(port=5000, debug=False)