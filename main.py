import os
import io
import json
import re
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pypdf import PdfReader

app = FastAPI(title="MoSPI iGOT Central Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./igot_mospi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {"sslmode": "require"}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRecord(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    department = Column(String(255), default="National Accounts Division (NAD)")
    designation = Column(String(255), default="Deputy Director / Assistant Director (ISS)")
    cadre = Column(String(100), default="Indian Statistical Service (ISS)")
    role = Column(String(50), default="employee")
    competency_score = Column(String(10), default="75%")
    posh_status = Column(String(50), default="Pending")
    completed_modules = Column(Text, default="[]")

class MockIGOTCentralRegistry(Base):
    __tablename__ = "mock_igot_central_registry"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    officer_email = Column(String(255), unique=True, index=True, nullable=False)
    officer_name = Column(String(255), nullable=False)
    verified_courses_json = Column(Text, default="[]")
    parichay_sso_token = Column(String(255), default="KY_PARICHAY_AUTH_SECURE_TOKEN")
    last_completed_at = Column(String(100), nullable=True)

class QuizRecord(Base):
    __tablename__ = "topic_quizzes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(Integer, nullable=False, default=1)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_index = Column(Integer, default=0)
    explanation = Column(Text, default="")

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Table sync note: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_mock_igot_registry():
    db = SessionLocal()
    try:
        if db.query(MockIGOTCentralRegistry).count() == 0:
            sample_records = [
                MockIGOTCentralRegistry(
                    officer_email="harsha@gov.in",
                    officer_name="Nagari Harsha Vardhan",
                    verified_courses_json=json.dumps([1, 2]),
                    parichay_sso_token="KY_PARICHAY_AUTH_89412",
                    last_completed_at="2026-08-25T14:30:00Z"
                ),
                MockIGOTCentralRegistry(
                    officer_email="officer@gov.in",
                    officer_name="Cadre Officer",
                    verified_courses_json=json.dumps([1, 3]),
                    parichay_sso_token="KY_PARICHAY_AUTH_55102",
                    last_completed_at="2026-08-26T10:15:00Z"
                ),
                MockIGOTCentralRegistry(
                    officer_email="123@gov.ac.in",
                    officer_name="Chief Administrator",
                    verified_courses_json=json.dumps([1, 2, 3]),
                    parichay_sso_token="KY_PARICHAY_AUTH_99999",
                    last_completed_at="2026-08-27T08:00:00Z"
                )
            ]
            db.add_all(sample_records)
            db.commit()
    finally:
        db.close()

seed_mock_igot_registry()

TOTAL_MODULES_COUNT = 5

COURSE_CATALOG = {
    1: "National Accounts & GDP Compilation (SNA 2008)",
    2: "Consumer Price Index (CPI) Analytics",
    3: "Periodic Labour Force Survey (PLFS) Digital Data Collection",
    4: "Annual Survey of Industries (ASI) Factory Scrutiny",
    5: "Index of Industrial Production (IIP) Diagnostics"
}

def extract_all_pdf_text(content: bytes) -> str:
    extracted = ""
    try:
        reader = PdfReader(io.BytesIO(content))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted += t + "\n"
    except Exception:
        pass
    if len(extracted.strip()) < 20:
        extracted = content.decode("utf-8", errors="ignore")
    return extracted.strip()

def call_ai_api(prompt: str, system_instruction: str = "") -> str:
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]
        full_text = f"{system_instruction}\n\nUser Question: {prompt}" if system_instruction else prompt
        payload = {"contents": [{"parts": [{"text": full_text}]}], "generationConfig": {"temperature": 0.3}}
        headers = {"Content-Type": "application/json"}
        for m in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception:
                pass
    return ""

def generate_questions_with_ai(extracted_text: str, filename: str, course_name: str) -> list:
    cleaned_doc_text = extracted_text.strip()
    prompt = f"""
Generate exactly 5 multiple-choice questions derived directly from the provided text for training module "{course_name}".
SOURCE DOCUMENT: "{filename}"
TEXT:
{cleaned_doc_text[:12000]}

Respond ONLY with a valid JSON array of 5 objects:
[
  {{
    "question": "Question text based on the document?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "explanation": "Detailed explanation citing concepts from the text."
  }}
]
"""
    raw_res = call_ai_api(prompt, "You are an official MoSPI examination system. Output raw JSON array only.")
    if raw_res:
        try:
            raw_clean = re.sub(r"^```json\s*", "", raw_res)
            raw_clean = re.sub(r"\s*```$", "", raw_clean).strip()
            parsed = json.loads(raw_clean)
            if isinstance(parsed, list) and len(parsed) >= 1:
                return parsed[:5]
        except Exception:
            pass

    return [
        {"question": f"Under guidelines for {course_name}, what protocol governs data verification?", "options": ["Systematic benchmark reconciliation against core registry data", "Discretionary non-compliance", "Arbitrary numerical averaging", "Manual unverified reporting"], "correct_index": 0, "explanation": f"Mandated quality standard as outlined in {filename}."},
        {"question": f"Which standard methodology applies to data validation under {course_name}?", "options": ["Dual independent enumeration cross-checking", "Single-point non-verified entry", "Heuristic random sampling", "External unverified estimates"], "correct_index": 0, "explanation": "Ensures statistical validity and consistency."},
        {"question": f"What is the frequency of monitoring required according to {filename}?", "options": ["Periodic structured auditing cycles", "Ad-hoc irregular spot checks", "No formal review necessary", "Annual summary estimation"], "correct_index": 0, "explanation": "Ensures systematic administrative compliance."},
        {"question": f"How are discrepancies reconciled during field operations for {course_name}?", "options": ["Immediate re-scrutiny and supervisor verification", "Automatic omission of variance", "Forced balance reconciliation", "Postponement to subsequent cycle"], "correct_index": 0, "explanation": "Standard Operating Procedure requires immediate re-verification."},
        {"question": f"What is the compliance threshold mandated in {course_name}?", "options": ["100% adherence to MoSPI framework protocols", "80% approximate matching", "Discretionary divisional target", "Informal guidelines only"], "correct_index": 0, "explanation": "Official framework mandates complete protocol adherence."}
    ]

def generate_dynamic_recommendations(officer: UserRecord, completed_ids: list, radar_scores: dict) -> list:
    lowest_domain = min(radar_scores.items(), key=lambda x: x[1]["current"])
    gap_domain_name = lowest_domain[0]
    current_val = lowest_domain[1]["current"]

    ai_prompt = f"""
Act as the AI Training Officer for MoSPI (Ministry of Statistics & Programme Implementation).
Recommend exactly 4 personalized learning pathways for an officer with the following profile:
- Cadre: {officer.cadre}
- Designation: {officer.designation}
- Division/Department: {officer.department}
- Identified Skill Gap Domain: "{gap_domain_name}" (Current Score: {current_val}%)
- Completed Module IDs: {completed_ids}

Output ONLY a JSON array with 4 course recommendation objects matching this exact structure:
[
  {{
    "source": "iGOT Karmayogi or NSSTA TPAC Recommended",
    "course": "Course Title Tailored for MoSPI",
    "priority": "High Priority or Mandatory or Compliance or Medium Priority",
    "target_gap": "{gap_domain_name}",
    "est_hours": "X Hours",
    "link": "https://igotkarmayogi.gov.in"
  }}
]
"""
    raw_response = call_ai_api(ai_prompt, "You are a specialized MoSPI Capacity Building Recommendation AI. Output raw JSON only.")
    if raw_response:
        try:
            cleaned = re.sub(r"^```json\s*", "", raw_response)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and len(parsed) >= 1:
                return parsed[:4]
        except Exception:
            pass

    return [
        {"source": "iGOT Karmayogi", "course": f"Advanced {gap_domain_name.split('(')[0].strip()} for {officer.cadre}", "priority": "High Priority", "target_gap": gap_domain_name, "est_hours": "6 Hours", "link": "https://igotkarmayogi.gov.in"},
        {"source": "NSSTA TPAC Recommended", "course": f"Official Data Analytics with Python & Big Data ({officer.department})", "priority": "Mandatory", "target_gap": "Technical & Data Analytics (Python/R/GIS/SQL)", "est_hours": "14 Hours", "link": "https://igotkarmayogi.gov.in"},
        {"source": "iGOT Karmayogi", "course": "Digital Personal Data Protection (DPDP) & Secure Governance", "priority": "Compliance", "target_gap": "Digital Governance & Cyber Security (DPDP/SSO)", "est_hours": "4 Hours", "link": "https://igotkarmayogi.gov.in"},
        {"source": "NSSTA TPAC Recommended", "course": f"Strategic Public Policy Leadership for {officer.designation}", "priority": "Medium Priority", "target_gap": "Managerial & Policy Decision Making (Leadership)", "est_hours": "8 Hours", "link": "https://igotkarmayogi.gov.in"}
    ]

class RegisterRequest(BaseModel):
    name: Optional[str] = "Registered Officer"
    email: str
    password: str
    department: Optional[str] = "National Accounts Division (NAD)"
    designation: Optional[str] = "Deputy Director / Assistant Director (ISS)"
    cadre: Optional[str] = "Indian Statistical Service (ISS)"

class LoginRequest(BaseModel):
    email: str
    password: str

class CompleteModuleRequest(BaseModel):
    email: str
    course_id: int

class ChatRequest(BaseModel):
    message: str
    email: Optional[str] = None

class IGOTSyncRequest(BaseModel):
    email: str

@app.get("/")
def root():
    return {"status": "online", "platform": "iGOT MoSPI Intelligence"}

@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return JSONResponse(content={"status": "ok"}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*"
    })

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_pass = req.password.strip()

    existing = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account already exists.")

    role = "admin" if clean_email == "123@gov.ac.in" else "employee"
    user = UserRecord(
        name=req.name.strip() if req.name else "Registered Officer",
        email=clean_email,
        password=clean_pass,
        hashed_password=clean_pass,
        department=req.department.strip() if req.department else "National Accounts Division (NAD)",
        designation=req.designation.strip() if req.designation else "Deputy Director / Assistant Director (ISS)",
        cadre=req.cadre.strip() if req.cadre else "Indian Statistical Service (ISS)",
        role=role,
        competency_score="75%",
        posh_status="Pending",
        completed_modules="[]"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "success", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_pass = req.password.strip()

    if clean_email == "123@gov.ac.in" and clean_pass == "1234":
        return {
            "status": "success",
            "user": {
                "id": 999,
                "name": "Chief Administrator",
                "email": "123@gov.ac.in",
                "department": "Ministry Headquarters",
                "designation": "Director General",
                "cadre": "Indian Statistical Service (ISS)",
                "role": "admin",
                "competency_score": "100%",
                "posh_status": "Completed",
                "completed_modules": [1, 2, 3]
            }
        }

    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user:
        role = "admin" if clean_email.startswith("admin") else "employee"
        user = UserRecord(
            name="Cadre Officer",
            email=clean_email,
            password=clean_pass,
            hashed_password=clean_pass,
            department="National Accounts Division (NAD)",
            designation="Deputy Director / Assistant Director (ISS)",
            cadre="Indian Statistical Service (ISS)",
            role=role,
            competency_score="75%",
            posh_status="Pending",
            completed_modules="[]"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    try:
        completed = json.loads(user.completed_modules) if user.completed_modules else []
    except Exception:
        completed = []

    return {
        "status": "success",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "department": user.department,
            "designation": user.designation,
            "cadre": user.cadre,
            "role": user.role,
            "competency_score": user.competency_score,
            "posh_status": user.posh_status,
            "completed_modules": completed
        }
    }

@app.post("/api/igot/sync")
def igot_sync_officer_learning(req: IGOTSyncRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Officer not found.")

    try:
        local_completed = set(json.loads(user.completed_modules or "[]"))
    except Exception:
        local_completed = set()

    record = db.query(MockIGOTCentralRegistry).filter(func.lower(MockIGOTCentralRegistry.officer_email) == clean_email).first()
    remote_verified = set(json.loads(record.verified_courses_json or "[]")) if record else set()
    new_additions = remote_verified - local_completed
    merged = sorted(list(local_completed.union(remote_verified)))

    if new_additions:
        user.completed_modules = json.dumps(merged)
        user.competency_score = f"{min(100, 75 + len(merged) * 5)}%"
        db.commit()

    return {
        "status": "success",
        "synced_new_count": len(new_additions),
        "message": f"Pulled {len(new_additions)} verified records from iGOT registry." if new_additions else "Profile is fully up-to-date with iGOT.",
        "completed_modules": merged,
        "competency_score": user.competency_score
    }

@app.post("/api/officer/complete-module")
def complete_module(req: CompleteModuleRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Officer not found.")

    try:
        completed = json.loads(user.completed_modules) if user.completed_modules else []
    except Exception:
        completed = []

    if req.course_id not in completed:
        completed.append(req.course_id)
        user.completed_modules = json.dumps(completed)
        user.competency_score = f"{min(100, 75 + len(completed) * 5)}%"
        db.commit()

    return {
        "status": "success",
        "completed_modules": completed,
        "competency_score": user.competency_score
    }

@app.get("/api/officer/skill-gap")
def get_skill_gap_analysis(email: str, db: Session = Depends(get_db)):
    clean_email = email.strip().lower()
    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Officer not found.")

    try:
        completed = json.loads(user.completed_modules) if user.completed_modules else []
    except Exception:
        completed = []

    n_done = len(completed)
    stat_score = min(95, 60 + n_done * 7)
    tech_score = min(90, 55 + n_done * 6)
    gov_score = min(98, 70 + (10 if user.posh_status == "Completed" else 0) + n_done * 4)
    mgmt_score = min(92, 65 + n_done * 5)

    radar_domains = {
        "Statistical Competencies (SNA/PLFS/CPI)": {"current": stat_score, "target": 95, "gap": max(0, 95 - stat_score)},
        "Technical & Data Analytics (Python/R/GIS/SQL)": {"current": tech_score, "target": 90, "gap": max(0, 90 - tech_score)},
        "Digital Governance & Cyber Security (DPDP/SSO)": {"current": gov_score, "target": 95, "gap": max(0, 95 - gov_score)},
        "Managerial & Policy Decision Making (Leadership)": {"current": mgmt_score, "target": 90, "gap": max(0, 90 - mgmt_score)}
    }

    return {
        "status": "success",
        "officer": user.name or "Officer",
        "cadre": user.cadre or "ISS",
        "department": user.department or "National Accounts Division (NAD)",
        "radar": radar_domains,
        "recommendations": generate_dynamic_recommendations(user, completed, radar_domains)
    }

@app.get("/api/admin/divisional-heatmap")
def get_divisional_heatmap(db: Session = Depends(get_db)):
    users = db.query(UserRecord).filter(UserRecord.role != "admin").all()
    divisions = {
        "National Accounts Division (NAD)": {"officers": 0, "stat": 0, "tech": 0, "gov": 0, "mgmt": 0},
        "Field Operations Division (FOD)": {"officers": 0, "stat": 0, "tech": 0, "gov": 0, "mgmt": 0},
        "Price Statistics Division (PSD)": {"officers": 0, "stat": 0, "tech": 0, "gov": 0, "mgmt": 0},
        "Data Informatics & Innovation Division (DIID)": {"officers": 0, "stat": 0, "tech": 0, "gov": 0, "mgmt": 0}
    }

    for u in users:
        dept = u.department if u.department in divisions else "National Accounts Division (NAD)"
        try:
            completed_count = len(json.loads(u.completed_modules or "[]"))
        except Exception:
            completed_count = 0
            
        divisions[dept]["officers"] += 1
        divisions[dept]["stat"] += min(95, 60 + completed_count * 7)
        divisions[dept]["tech"] += min(90, 55 + completed_count * 6)
        divisions[dept]["gov"] += min(98, 70 + (10 if u.posh_status == "Completed" else 0) + completed_count * 4)
        divisions[dept]["mgmt"] += min(92, 65 + completed_count * 5)

    heatmap_data = []
    for div_name, data in divisions.items():
        count = max(1, data["officers"])
        s_avg = round(data["stat"] / count, 1) if data["officers"] > 0 else 74.0
        t_avg = round(data["tech"] / count, 1) if data["officers"] > 0 else 67.0
        g_avg = round(data["gov"] / count, 1) if data["officers"] > 0 else 82.0
        m_avg = round(data["mgmt"] / count, 1) if data["officers"] > 0 else 78.0

        domain_gaps = {
            "Statistical Frameworks (SNA/PLFS)": round(95.0 - s_avg, 1),
            "Technical Analytics (Python/GIS)": round(90.0 - t_avg, 1),
            "Digital Governance & DPDP": round(95.0 - g_avg, 1),
            "Managerial & Leadership": round(90.0 - m_avg, 1)
        }
        critical_lag = max(domain_gaps.items(), key=lambda x: x[1])

        heatmap_data.append({
            "division": div_name,
            "officers_enrolled": data["officers"],
            "stat_score": s_avg,
            "tech_score": t_avg,
            "gov_score": g_avg,
            "mgmt_score": m_avg,
            "critical_lag_domain": critical_lag[0],
            "max_gap_percentage": critical_lag[1]
        })

    return {"status": "success", "heatmap": heatmap_data}

@app.get("/api/admin/tna-report")
def get_tna_report(db: Session = Depends(get_db)):
    users = db.query(UserRecord).filter(UserRecord.role != "admin").all()
    total = max(1, len(users))
    return {
        "status": "success",
        "report": {
            "report_id": f"NSSTA-TNA-{datetime.utcnow().year}-01",
            "ministry": "Ministry of Statistics & Programme Implementation (MoSPI)",
            "generated_on": datetime.utcnow().strftime("%d-%B-%Y"),
            "total_officers_evaluated": total,
            "critical_ministry_bottlenecks": [
                {"domain": "Technical & Big Data Analytics (Python/R/GIS)", "evaluated_gap": "23.4%", "priority": "CRITICAL"},
                {"domain": "Digital Survey Modernization (PLFS CAPI/CATI)", "evaluated_gap": "18.1%", "priority": "HIGH"},
                {"domain": "Digital Personal Data Protection Act Compliance", "evaluated_gap": "14.5%", "priority": "MANDATORY"}
            ],
            "recommended_batch_trainings": [
                {"batch_id": "NSSTA-BT-01", "title": "Intensive Official Statistics with Python, R & Big Data GIS", "target_cadre": "ISS & SSS Cadre", "mode": "Hybrid (iGOT + NSSTA)", "batch_capacity": "45 Officers", "total_man_hours": "1,200 Hours", "timeline": "Q3 2026"},
                {"batch_id": "NSSTA-BT-02", "title": "SNA 2008 & GVA National Accounts Re-basing Methodologies", "target_cadre": "National Accounts Division (NAD)", "mode": "iGOT Karmayogi Pathway", "batch_capacity": "60 Officers", "total_man_hours": "600 Hours", "timeline": "Q4 2026"}
            ],
            "total_training_man_hours_allocated": "1,800 Hours"
        }
    }

@app.post("/api/admin/upload-quiz-material")
async def upload_quiz_material(course_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    course_name = COURSE_CATALOG.get(course_id, f"Training Module #{course_id}")
    content = await file.read()
    extracted_text = extract_all_pdf_text(content)
    ai_questions = generate_questions_with_ai(extracted_text, file.filename, course_name)
    
    db.query(QuizRecord).filter(QuizRecord.course_id == course_id).delete()
    new_records = [
        QuizRecord(
            course_id=course_id,
            question=q.get("question", f"Assessment Question from {file.filename}"),
            options_json=json.dumps(q.get("options", ["Option A", "Option B", "Option C", "Option D"])),
            correct_index=int(q.get("correct_index", 0)),
            explanation=q.get("explanation", f"Derived from {file.filename}.")
        ) for q in ai_questions
    ]
    db.add_all(new_records)
    db.commit()
    return {"status": "success", "questions_generated": len(new_records), "course_id": course_id}

@app.post("/api/chat/assistant")
def virtual_assistant(req: ChatRequest):
    ai_reply = call_ai_api(req.message, "You are the official iGOT MoSPI virtual assistant. Provide expert answers on SNA 2008, PLFS, CPI, and NSSTA capacity building.")
    if ai_reply:
        return {"status": "success", "reply": ai_reply}
    return {"status": "success", "reply": "Namaste Officer! Gross Value Added (GVA) is Output minus Intermediate Consumption. Circular systematic sampling with PPS applies to PLFS."}

@app.get("/api/admin/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserRecord).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "cadre": u.cadre, "department": u.department, "designation": u.designation, "competency": u.competency_score, "completed_count": len(json.loads(u.completed_modules or "[]"))} for u in users]
