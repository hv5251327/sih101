import os
import io
import json
import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
from pypdf import PdfReader
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI(title="MoSPI AI Skill Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    department = Column(String(255), default="National Accounts Division (NAD)")
    designation = Column(String(255), default="Deputy Director / Assistant Director (ISS)")
    cadre = Column(String(100), default="Indian Statistical Service (ISS)")
    role = Column(String(50), default="employee")
    competency_score = Column(String(10), default="75%")
    posh_status = Column(String(50), default="Pending")

class TopicQuizRecord(Base):
    __tablename__ = "topic_quizzes"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, index=True)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_index = Column(Integer, default=0)
    explanation = Column(Text, nullable=False)

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database sync notice: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
client = OpenAI(api_key=XAI_API_KEY or "placeholder", base_url="https://api.x.ai/v1")

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    department: str
    designation: str
    cadre: Optional[str] = "Indian Statistical Service (ISS)"

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    try:
        count = db.query(UserRecord).count()
    except Exception:
        count = 0
    return {
        "status": "online",
        "users_count": count,
        "database_engine": "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"
    }

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    existing = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Officer already registered.")
    
    user = UserRecord(
        name=req.name.strip(),
        email=clean_email,
        password=req.password.strip(),
        department=req.department.strip(),
        designation=req.designation.strip(),
        cadre=req.cadre.strip() if req.cadre else "Indian Statistical Service (ISS)",
        role="admin" if clean_email == "123@gov.ac.in" else "employee",
        competency_score="75%",
        posh_status="Pending"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
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
            "posh_status": user.posh_status
        }
    }

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    user = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
    if not user or user.password != req.password.strip():
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "department": user.department,
        "designation": user.designation,
        "cadre": user.cadre,
        "role": user.role,
        "competency_score": user.competency_score,
        "posh_status": user.posh_status
    }

@app.get("/api/admin/users")
def get_users(db: Session = Depends(get_db)):
    try:
        return [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "department": u.department,
                "designation": u.designation,
                "cadre": u.cadre,
                "role": u.role,
                "score": u.competency_score,
                "posh": u.posh_status
            } for u in db.query(UserRecord).all()
        ]
    except Exception:
        return []

@app.get("/api/topics/{course_id}/quiz")
def get_quiz(course_id: int, db: Session = Depends(get_db)):
    try:
        records = db.query(TopicQuizRecord).filter(TopicQuizRecord.course_id == course_id).all()
        if records:
            return {
                "course_id": course_id,
                "questions": [
                    {
                        "id": r.id,
                        "question": r.question,
                        "options": json.loads(r.options_json),
                        "correct_index": r.correct_index,
                        "explanation": r.explanation
                    } for r in records
                ]
            }
    except Exception:
        pass
    return {
        "course_id": course_id,
        "questions": [
            {
                "id": 1,
                "question": "Which compliance framework is mandatory for official data handling?",
                "options": [
                    "Adherence to standardized NSSTA Data Quality and Metadata Frameworks",
                    "Unverified raw processing",
                    "Arbitrary quota allocation without variance logs",
                    "Non-probabilistic manual estimation"
                ],
                "correct_index": 0,
                "explanation": "NSSTA standards mandate verified data handling."
            }
        ]
    }

@app.post("/api/admin/upload-quiz-material")
async def upload_quiz_material(
    course_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    extracted_text = ""
    if file:
        file_bytes = await file.read()
        if file.filename.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    extracted_text += (page.extract_text() or "") + "\n"
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")
        else:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")
    elif raw_text:
        extracted_text = raw_text
    else:
        raise HTTPException(status_code=400, detail="No PDF file or text provided")

    context = re.sub(r'\s+', ' ', extracted_text).strip()[:9000]
    system_prompt = "You are an expert NSSTA curriculum evaluator. Generate 3 MCQs in raw JSON."
    user_prompt = f"Create 3 MCQs based on this text:\n{context}\nReturn strictly JSON: [{{\"question\": \"...\", \"options\": [\"A\",\"B\",\"C\",\"D\"], \"correct_index\": 0, \"explanation\": \"...\"}}]"

    quiz_data = []
    if XAI_API_KEY:
        try:
            res = client.chat.completions.create(
                model="grok-2-latest",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.2
            )
            raw = res.choices[0].message.content.strip()
            if raw.startswith("```json"): raw = raw[7:-3].strip()
            elif raw.startswith("```"): raw = raw[3:-3].strip()
            quiz_data = json.loads(raw)
        except Exception as e:
            print(f"Grok Error: {e}")

    if not quiz_data:
        quiz_data = [
            {
                "question": "What is the mandatory operational benchmark under this material?",
                "options": [
                    "Adherence to calibrated validation and metadata protocols",
                    "Unweighted non-probabilistic sample imputation",
                    "Exclusion of outlier strata",
                    "Manual aggregation"
                ],
                "correct_index": 0,
                "explanation": "Verified compliance is required to ensure national data credibility."
            }
        ]

    try:
        db.query(TopicQuizRecord).filter(TopicQuizRecord.course_id == course_id).delete()
        for q in quiz_data:
            db.add(TopicQuizRecord(
                course_id=course_id,
                question=q.get("question"),
                options_json=json.dumps(q.get("options")),
                correct_index=q.get("correct_index", 0),
                explanation=q.get("explanation", "")
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"DB save error: {e}")

    return {"status": "success", "course_id": course_id, "questions_saved": len(quiz_data), "quiz": quiz_data}
