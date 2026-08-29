import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import urllib.parse

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "igot_mospi.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
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

@app.route("/api/officer/recommendations", methods=["POST"])
def get_recommendations():
    data = request.json or {}
    email = data.get("email", "officer@gov.in")
    designation = data.get("designation", "Junior Statistical Officer (JSO)")
    cadre = get_cadre(designation)
    mods = VIDEO_CATALOG.get(cadre, VIDEO_CATALOG["SSS"])

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

# Direct Free Google/Bhashini Multi-Language API Endpoint
@app.route("/api/translate", methods=["POST"])
def translate():
    data = request.json or {}
    texts = data.get("texts", [])
    target = data.get("target_lang", "en")
    
    if target == "en" or not texts:
        return jsonify({"translations": texts})

    translated = []
    for t in texts:
        if not t.strip():
            translated.append(t)
            continue
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target}&dt=t&q={urllib.parse.quote(t)}"
            res = requests.get(url, timeout=5).json()
            translated.append(res[0][0][0] if res and res[0] and res[0][0] else t)
        except Exception:
            translated.append(t)

    return jsonify({"translations": translated})

@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    data = request.json or {}
    msg = data.get("message", "").lower()
    desig = data.get("designation", "Statistical Officer")
    if "pillar" in msg or "competency" in msg:
        reply = "MoSPI tests 4 core pillars: Statistical Frameworks, Technical Tools & Computing, Digital Governance (DPDP), and Behavioural Management."
    elif "certificate" in msg or "video" in msg:
        reply = f"For your role as {desig}, complete each module and upload its certificate to update that pillar's verified completion score."
    elif "gap" in msg:
        reply = "The gap percentage represents the difference between your completed courses and the NSSTA target benchmark."
    else:
        reply = f"Namaste! As your MoSPI Learning AI Assistant, I can guide you through the training roadmap mapped to {desig}."
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(port=5000, debug=False)