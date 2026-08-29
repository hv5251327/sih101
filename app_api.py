import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from deep_translator import GoogleTranslator

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "igot_mospi.db")

# Master Video Repository Tailored by Cadre / Designation Specificity
VIDEO_CATALOG = {
    # ISS Cadre (Group A - Strategic, SNA, Sampling Theory, Big Data, DPDP Strategy)
    "ISS": [
        {"id": "iss-stat-1", "title": "SNA 2008 / 2025: National Accounts & Macro Aggregates Compilation", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-stat-2", "title": "Advanced Survey Design, Stratification & Survey Weight Calibration", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-tech-1", "title": "Official Data Pipelines using Python, R & Cloud Analytics", "pillar": "technical", "pillarTitle": "Technical Tools & Computing", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-tech-2", "title": "AI/ML Applications in Official Sample Validation & Imputation", "pillar": "technical", "pillarTitle": "Technical Tools & Computing", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-gov-1", "title": "DPDP Act 2023 Compliance & National Data Governance Architecture", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "iss-beh-1", "title": "Apex Statistical Leadership, Evidence-Based Policy & Negotiation", "pillar": "behavioural", "pillarTitle": "Behavioural & Management", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"}
    ],
    # SSS Cadre (Group B - Primary Data, CAPI, Field Audits, GIS Ground Truthing)
    "SSS": [
        {"id": "sss-stat-1", "title": "PLFS & ASUSE Schedule Filling & Validation Guidelines", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-stat-2", "title": "Consumer Price Index (CPI) Rural & Urban Quotation Protocols", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-tech-1", "title": "CAPI Tablet Application Operations & Real-Time Data Sync", "pillar": "technical", "pillarTitle": "Technical Tools & Computing", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-tech-2", "title": "Bhuvan GIS Ground Truthing & Urban Frame Survey (UFS) Mapping", "pillar": "technical", "pillarTitle": "Technical Tools & Computing", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-gov-1", "title": "Field Data Security, Respondent Privacy & Consent Management", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "sss-beh-1", "title": "Field Team Supervision, Active Interviewing & Public Interaction", "pillar": "behavioural", "pillarTitle": "Behavioural & Management", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"}
    ],
    # State DES Cadre (GSDP, District Statistics, Agriculture, CRS)
    "DES": [
        {"id": "des-stat-1", "title": "Gross State Domestic Product (GSDP) & State Income Estimation", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-stat-2", "title": "Crop Estimation Surveys (EARAS) & State Agricultural Statistics", "pillar": "statistical", "pillarTitle": "Statistical Frameworks", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-tech-1", "title": "State Statistical Portals & Open Data Dashboard Management", "pillar": "technical", "pillarTitle": "Technical Tools & Computing", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-tech-2", "title": "Spreadsheet Automation & District Level Tabulation Packages", "pillar": "technical", "pillarTitle": "Technical Tools & Computing", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-gov-1", "title": "Civil Registration System (CRS) Standards & State-Centre Sharing", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
        {"id": "des-beh-1", "title": "District Administration Liaison & Enumerator Team Coordination", "pillar": "behavioural", "pillarTitle": "Behavioural & Management", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"}
    ]
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 1. AI Recommendation Endpoint based on Designation
@app.route("/api/officer/recommendations", methods=["POST"])
def get_recommendations():
    data = request.json or {}
    email = data.get("email", "officer@gov.in")
    designation = data.get("designation", "")

    # Determine Cadre Category
    if "ISS" in designation or "Director General" in designation or "Director (" in designation or "Deputy Director" in designation or "Assistant Director" in designation:
        cadre_group = "ISS"
    elif "DES" in designation or "State" in designation or "District" in designation:
        cadre_group = "DES"
    else:
        cadre_group = "SSS"

    recommended_list = VIDEO_CATALOG.get(cadre_group, VIDEO_CATALOG["SSS"])

    # Persist recommendations to DB for tracking
    conn = get_db()
    cursor = conn.cursor()
    for mod in recommended_list:
        cursor.execute("""
            INSERT OR IGNORE INTO officer_recommendations 
            (officer_email, designation_name, module_id, module_title, pillar, embed_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, designation, mod["id"], mod["title"], mod["pillar"], mod["embedUrl"]))
    conn.commit()

    # Query completed status
    cursor.execute("SELECT module_id, is_completed FROM officer_recommendations WHERE officer_email = ?", (email,))
    completed_map = {row["module_id"]: bool(row["is_completed"]) for row in cursor.fetchall()}
    conn.close()

    response_modules = []
    for mod in recommended_list:
        m = dict(mod)
        m["is_completed"] = completed_map.get(mod["id"], False)
        response_modules.append(m)

    return jsonify({"cadre_group": cadre_group, "modules": response_modules})

# 2. Update Progress & Recalculate Percentage in DB
@app.route("/api/officer/progress", methods=["POST"])
def update_progress():
    data = request.json or {}
    email = data.get("email", "officer@gov.in")
    module_id = data.get("module_id", "")
    pillar = data.get("pillar", "statistical")

    conn = get_db()
    cursor = conn.cursor()
    
    # Mark module as completed
    cursor.execute("UPDATE officer_recommendations SET is_completed = 1 WHERE officer_email = ? AND module_id = ?", (email, module_id))
    
    # Count completed vs total modules for this pillar
    cursor.execute("SELECT COUNT(*) FROM officer_recommendations WHERE officer_email = ? AND pillar = ?", (email, pillar))
    total_in_pillar = cursor.fetchone()[0] or 1
    
    cursor.execute("SELECT COUNT(*) FROM officer_recommendations WHERE officer_email = ? AND pillar = ? AND is_completed = 1", (email, pillar))
    completed_in_pillar = cursor.fetchone()[0]

    percentage = int(round((completed_in_pillar / total_in_pillar) * 100))

    col_map = {
        "statistical": "current_statistical",
        "technical": "current_technical",
        "governance": "current_governance",
        "behavioural": "current_behavioural"
    }
    col = col_map.get(pillar, "current_statistical")
    cursor.execute(f"UPDATE officer_profiles SET {col} = ? WHERE email = ?", (percentage, email))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "pillar": pillar, "new_percentage": percentage, "completed": completed_in_pillar, "total": total_in_pillar})

# 3. Google Translate Translation Endpoint for Dashboard
@app.route("/api/translate", methods=["POST"])
def translate_text():
    data = request.json or {}
    texts = data.get("texts", [])
    target_lang = data.get("target_lang", "en")

    if target_lang == "en":
        return jsonify({"translations": texts})

    try:
        translator = GoogleTranslator(source="en", target=target_lang)
        translated_list = [translator.translate(t) for t in texts]
        return jsonify({"translations": translated_list})
    except Exception as e:
        return jsonify({"translations": texts, "error": str(e)})

# 4. Interactive AI Chatbot Endpoint
@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    data = request.json or {}
    msg = data.get("message", "").lower()
    desig = data.get("designation", "Officer")

    if "pillar" in msg or "competency" in msg:
        reply = "Your profile is evaluated across 4 pillars: Statistical, Technical, Digital Governance, and Behavioural. Videos are tailored specifically to your designation."
    elif "video" in msg or "course" in msg or "recommend" in msg:
        reply = f"For your role as {desig}, specific advanced modules are allocated. Uploading each module's certificate calculates and updates your pillar proficiency in the database."
    elif "gap" in msg:
        reply = "The gap shows how much additional verified training is required to reach the NSSTA national benchmark for your designation."
    else:
        reply = f"Hello! As the MoSPI AI Learning Assistant, I can guide you through the training roadmap mapped to {desig}."

    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(port=5000, debug=False)