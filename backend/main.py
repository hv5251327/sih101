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

app = FastAPI(title="MoSPI AI Skill Intelligence & iGOT Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./igot_mospi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
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

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Seed Admin & Default Records
def seed_initial_data():
    db = SessionLocal()
    if not db.query(UserRecord).filter(UserRecord.email == "123@gov.ac.in").first():
        db.add(UserRecord(
            name="Master Administrator",
            email="123@gov.ac.in",
            password="1234",
            department="Capacity Building Commission",
            designation="Chief Administrator",
            cadre="Commission",
            role="admin",
            competency_score="100%",
            posh_status="Completed"
        ))
    if not db.query(UserRecord).filter(UserRecord.email == "rajesh.k@mospi.gov.in").first():
        db.add(UserRecord(
            name="Shri Rajesh Kumar",
            email="rajesh.k@mospi.gov.in",
            password="1234",
            department="National Accounts Division (NAD)",
            designation="Deputy Director / Assistant Director (ISS)",
            cadre="Indian Statistical Service (ISS)",
            role="employee",
            competency_score="75%",
            posh_status="Completed"
        ))
    if db.query(TopicQuizRecord).count() == 0:
        db.add(TopicQuizRecord(
            course_id=7,
            question="Under the POSH Act 2013, within what maximum timeframe must an Internal Committee (IC) complete an inquiry?",
            options_json=json.dumps([
                "Within 90 days from complaint receipt",
                "Within 30 days of initial notice",
                "Within 180 days of annual report",
                "Within 15 days of hearings"
            ]),
            correct_index=0,
            explanation="Section 11(4) of the POSH Act mandates completion within 90 days."
        ))
    db.commit()
    db.close()

seed_initial_data()

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
    return {
        "status": "MoSPI Skill Intelligence Backend Active",
        "registered_users": db.query(UserRecord).count(),
        "stored_quiz_questions": db.query(TopicQuizRecord).count()
    }

@app.post("/api/register")
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    existing = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An official with this email is already registered.")
    
    new_user = UserRecord(
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
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "status": "success",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "department": new_user.department,
            "designation": new_user.designation,
            "cadre": new_user.cadre,
            "role": new_user.role,
            "competency_score": new_user.competency_score,
            "posh_status": new_user.posh_status
        }
    }

@app.post("/api/login")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    user = db.query(UserRecord).filter(UserRecord.email == clean_email).first()
    if not user or user.password != req.password.strip():
        raise HTTPException(status_code=401, detail="Invalid official credentials.")
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
def get_all_users(db: Session = Depends(get_db)):
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

@app.get("/api/topics/{course_id}/quiz")
def get_topic_quiz(course_id: int, db: Session = Depends(get_db)):
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
    return {
        "course_id": course_id,
        "questions": [
            {
                "id": 1,
                "question": "Which compliance framework is mandatory for official data handling under this topic?",
                "options": [
                    "Adherence to standardized NSSTA Data Quality and Metadata Frameworks",
                    "Unverified raw processing",
                    "Arbitrary quota allocation without variance logs",
                    "Non-probabilistic manual estimation"
                ],
                "correct_index": 0,
                "explanation": "NSSTA standards mandate full verification and metadata preservation for official statistics."
            }
        ]
    }
