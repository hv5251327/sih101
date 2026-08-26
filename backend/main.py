import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import jwt, JWTError
from openai import OpenAI

# ----------------- SECURITY & CONFIG -----------------
SECRET_KEY = os.environ.get("SECRET_KEY", "sih-mospi-secret-key-production-change-in-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # Truncate to 72 bytes to adhere to bcrypt specification limits
    return pwd_context.hash(password[:72])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ----------------- AI CLIENT CONFIG -----------------
# Supports Groq (Llama-3) or xAI Grok
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", os.environ.get("XAI_API_KEY", ""))
IS_GROQ = GROQ_API_KEY.startswith("gsk_")

ai_client = OpenAI(
    api_key=GROQ_API_KEY or "dummy-key-for-init",
    base_url="https://api.groq.com/openai/v1" if IS_GROQ else "https://api.x.ai/v1"
)
AI_MODEL = "llama-3.3-70b-versatile" if IS_GROQ else "grok-beta"

# ----------------- DATABASE SCHEMA -----------------
RAW_DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./sih101.db")
if RAW_DB_URL.startswith("postgres://"):
    RAW_DB_URL = RAW_DB_URL.replace("postgres://", "postgresql://", 1)

DATABASE_URL = RAW_DB_URL
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    designation = Column(String(100), nullable=False)
    department = Column(String(150), nullable=False)
    competency_score = Column(Integer, default=25)
    created_at = Column(DateTime, default=datetime.utcnow)
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    logins = relationship("LoginAudit", back_populates="user", cascade="all, delete-orphan")

class LoginAudit(Base):
    __tablename__ = "login_audits"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(120), ForeignKey("users.email"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="logins")

class Course(Base):
    __tablename__ = "courses"
    course_id = Column(String(50), primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    domain = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    video_url = Column(String(255), nullable=False)

class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(120), ForeignKey("users.email"), nullable=False)
    course_id = Column(String(50), ForeignKey("courses.course_id"), nullable=False)
    video_completed = Column(Boolean, default=False)
    quiz_completed = Column(Boolean, default=False)
    quiz_score = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="progress")

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String(50), ForeignKey("courses.course_id"), nullable=False)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_idx = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------- SEED BASELINE DATA -----------------
def seed_production_baseline():
    db = SessionLocal()
    if db.query(Course).count() == 0:
        courses = [
            Course(course_id="STAT101", title="Sampling Techniques & Large Scale Survey Design", domain="Core Statistics", description="Stratified, cluster, and multi-stage frameworks for NSSO socio-economic rounds.", video_url="https://www.youtube.com/embed/rfscVS0vtbw"),
            Course(course_id="TECH201", title="Python & Data Wrangling for Official Statistics", domain="Data Science", description="Pandas transformations, outlier handling, and imputation for microdata.", video_url="https://www.youtube.com/embed/rfscVS0vtbw"),
            Course(course_id="GOV301", title="Data Governance, Metadata & Open Data Standards", domain="Governance", description="NDSAP guidelines, metadata cataloging, and secure API data delivery.", video_url="https://www.youtube.com/embed/rfscVS0vtbw"),
            Course(course_id="STAT202", title="National Accounts & GDP Deflator Estimation", domain="Core Statistics", description="Gross Value Added (GVA) estimation, base revisions, and price indexing.", video_url="https://www.youtube.com/embed/rfscVS0vtbw")
        ]
        db.add_all(courses)
        db.commit()

        quizzes = [
            QuizQuestion(course_id="STAT101", question="What is the key advantage of Stratified Random Sampling over SRS?", options_json=json.dumps(["Ensures representation across diverse subgroups to reduce variance", "Requires no prior sampling frame", "Completely eliminates non-sampling error", "Is always cheaper than cluster sampling"]), correct_idx=0, explanation="Stratification creates homogeneous strata, minimizing within-stratum variance."),
            QuizQuestion(course_id="STAT101", question="Which wing conducts nationwide socio-economic household rounds?", options_json=json.dumps(["National Sample Survey Office (NSSO)", "Central Statistics Office (CSO)", "NITI Aayog", "Reserve Bank of India"]), correct_idx=0, explanation="NSSO is the survey wing of MoSPI."),
            QuizQuestion(course_id="TECH201", question="Which Pandas method accurately detects missing/NaN cells?", options_json=json.dumps(["df.isna() / df.isnull()", "df.empty()", "df.clean_nulls()", "df.drop_blanks()"]), correct_idx=0, explanation="isna() produces a boolean mask for null data points."),
            QuizQuestion(course_id="GOV301", question="What is the mandate of NDSAP?", options_json=json.dumps(["National Data Sharing and Accessibility Policy", "National Digital Statistics Action Plan", "Network Data Safety and Privacy", "None of the above"]), correct_idx=0, explanation="NDSAP standardizes sharing public non-sensitive datasets.")
        ]
        db.add_all(quizzes)
        db.commit()

    if db.query(User).filter(User.email == "emp@mospi.gov.in").count() == 0:
        db.add(User(
            name="Ramesh Kumar",
            email="emp@mospi.gov.in",
            hashed_password=hash_password("password123"),
            designation="Junior Statistical Officer (JSO)",
            department="National Sample Survey Office (NSSO)",
            competency_score=40
        ))
        db.commit()
    db.close()

seed_production_baseline()

# ----------------- FASTAPI APPLICATION -----------------
app = FastAPI(title="MoSPI Skill Intelligence Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- SCHEMAS -----------------
class RegisterSchema(BaseModel):
    name: str
    email: str
    password: str
    designation: str
    department: str

class LoginSchema(BaseModel):
    email: str
    password: str

class VideoCompleteSchema(BaseModel):
    email: str
    course_id: str

class QuizSubmitSchema(BaseModel):
    email: str
    course_id: str
    answers: List[int]

# ----------------- ENDPOINTS -----------------
@app.get("/")
def health_check():
    return {"status": "healthy", "service": "MoSPI Skill Intelligence Platform API"}

@app.post("/api/register")
def register_user(payload: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Officer email already registered.")
    
    new_officer = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        designation=payload.designation,
        department=payload.department,
        competency_score=25
    )
    db.add(new_officer)
    db.commit()
    return {"message": "Officer registration completed."}

@app.post("/api/login")
def login_user(payload: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid official credentials.")
    
    db.add(LoginAudit(user_email=user.email))
    db.commit()
    
    token = create_access_token({"sub": user.email, "role": "officer"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": user.name,
            "email": user.email,
            "designation": user.designation,
            "department": user.department,
            "competency_score": user.competency_score
        }
    }

@app.get("/api/dashboard/{email}")
def get_dashboard(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Officer not found.")
    
    courses = db.query(Course).all()
    progress_records = {p.course_id: p for p in db.query(UserProgress).filter(UserProgress.user_email == email).all()}
    
    todo, done = [], []
    for c in courses:
        p = progress_records.get(c.course_id)
        item = {
            "course_id": c.course_id,
            "title": c.title,
            "domain": c.domain,
            "description": c.description,
            "video_url": c.video_url,
            "video_completed": p.video_completed if p else False,
            "quiz_completed": p.quiz_completed if p else False,
            "quiz_score": p.quiz_score if p else 0
        }
        if p and p.quiz_completed:
            done.append(item)
        else:
            todo.append(item)
            
    return {
        "profile": {
            "name": user.name,
            "email": user.email,
            "designation": user.designation,
            "department": user.department,
            "competency_score": user.competency_score
        },
        "stats": {
            "total_courses": len(courses),
            "completed_count": len(done),
            "pending_count": len(todo)
        },
        "todo_courses": todo,
        "completed_courses": done
    }

@app.post("/api/complete-video")
def complete_video(payload: VideoCompleteSchema, db: Session = Depends(get_db)):
    prog = db.query(UserProgress).filter(UserProgress.user_email == payload.email, UserProgress.course_id == payload.course_id).first()
    if not prog:
        prog = UserProgress(user_email=payload.email, course_id=payload.course_id, video_completed=True)
        db.add(prog)
    else:
        prog.video_completed = True
    db.commit()
    return {"message": "Video completion logged."}

@app.get("/api/quiz/{course_id}")
def fetch_quiz(course_id: str, db: Session = Depends(get_db)):
    questions = db.query(QuizQuestion).filter(QuizQuestion.course_id == course_id).all()
    return {
        "course_id": course_id,
        "questions": [{"id": q.id, "question": q.question, "options": json.loads(q.options_json)} for q in questions]
    }

@app.post("/api/submit-quiz")
def evaluate_quiz(sub: QuizSubmitSchema, db: Session = Depends(get_db)):
    questions = db.query(QuizQuestion).filter(QuizQuestion.course_id == sub.course_id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="Questions not configured.")
        
    score = 0
    review = []
    for idx, q in enumerate(questions):
        user_ans = sub.answers[idx] if idx < len(sub.answers) else -1
        correct = (user_ans == q.correct_idx)
        if correct:
            score += 1
        review.append({
            "question": q.question,
            "options": json.loads(q.options_json),
            "user_answer": user_ans,
            "correct_answer": q.correct_idx,
            "is_correct": correct,
            "explanation": q.explanation or "Standard curriculum concept."
        })
        
    passed = score >= (len(questions) * 0.5)
    if passed:
        prog = db.query(UserProgress).filter(UserProgress.user_email == sub.email, UserProgress.course_id == sub.course_id).first()
        if not prog:
            prog = UserProgress(user_email=sub.email, course_id=sub.course_id, video_completed=True, quiz_completed=True, quiz_score=score)
            db.add(prog)
        else:
            prog.quiz_completed = True
            prog.quiz_score = score
            
        user = db.query(User).filter(User.email == sub.email).first()
        if user:
            user.competency_score = min(100, user.competency_score + 20)
        db.commit()
        
    return {"passed": passed, "score": score, "total": len(questions), "review": review}

@app.post("/api/verify-certificate")
async def verify_certificate(
    email: str = Form(...),
    course_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    reader = PdfReader(file.file)
    extracted_text = " ".join([p.extract_text() or "" for p in reader.pages]).strip()

    if len(extracted_text) < 30:
        raise HTTPException(status_code=400, detail="Unable to extract readable text from PDF.")

    user = db.query(User).filter(User.email == email).first()
    course = db.query(Course).filter(Course.course_id == course_id).first()
    if not user or not course:
        raise HTTPException(status_code=404, detail="User or course record not found.")

    if GROQ_API_KEY:
        prompt = f"""
        You are an audit verification engine for India's Official Statistics System (MoSPI/iGOT Karmayogi).
        Verify if this certificate text confirms that officer '{user.name}' completed the course '{course.title}' ({course.course_id}).

        Certificate Text:
        \"\"\"{extracted_text[:3000]}\"\"\"

        Return ONLY a JSON object:
        {{
          "is_valid": true/false,
          "confidence_score": 0.0 to 1.0,
          "issuer": "detected issuer name",
          "reason": "short explanation"
        }}
        """
        try:
            res = ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "You output strict JSON objects only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            raw = res.choices[0].message.content.strip()
            clean = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
            decision = json.loads(clean)
            is_valid = decision.get("is_valid") and decision.get("confidence_score", 0) >= 0.65
            reason = decision.get("reason", "Verified via AI analysis.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI verification failure: {str(e)}")
    else:
        # Fallback keyword match if no API key is provided
        is_valid = any(k in extracted_text.lower() for k in ["karmayogi", "mospi", "nssta", "certificate", "completion"])
        reason = "Verified via official training keywords."

    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Certificate verification rejected: {reason}")

    prog = db.query(UserProgress).filter(UserProgress.user_email == email, UserProgress.course_id == course_id).first()
    if not prog:
        prog = UserProgress(user_email=email, course_id=course_id, video_completed=True, quiz_completed=True, quiz_score=100)
        db.add(prog)
    else:
        prog.video_completed = True
        prog.quiz_completed = True

    user.competency_score = min(100, user.competency_score + 20)
    db.commit()
    return {"message": f"Certificate verified successfully: {reason}"}

@app.get("/api/admin/analytics")
def get_analytics(db: Session = Depends(get_db)):
    users = db.query(User).all()
    courses = db.query(Course).all()
    
    roster = []
    cadre_stats = {}
    
    for u in users:
        completed = db.query(UserProgress).filter(UserProgress.user_email == u.email, UserProgress.quiz_completed == True).all()
        done_ids = {p.course_id for p in completed}
        pending = [c.title for c in courses if c.course_id not in done_ids]
        
        roster.append({
            "name": u.name,
            "email": u.email,
            "designation": u.designation,
            "department": u.department,
            "competency_score": u.competency_score,
            "completed_count": len(done_ids),
            "pending_courses": pending
        })
        if u.designation not in cadre_stats:
            cadre_stats[u.designation] = {"count": 0, "score_sum": 0}
        cadre_stats[u.designation]["count"] += 1
        cadre_stats[u.designation]["score_sum"] += u.competency_score
        
    summary = [{"designation": k, "count": v["count"], "avg_score": round(v["score_sum"] / v["count"], 1)} for k, v in cadre_stats.items()]
    return {"total_officers": len(users), "total_courses": len(courses), "cadre_summary": summary, "roster": roster}

@app.post("/api/admin/generate-quiz-pdf")
async def generate_quiz_pdf(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    reader = PdfReader(file.file)
    extracted = " ".join([p.extract_text() or "" for p in reader.pages]).strip()
    
    if len(extracted) < 40:
        raise HTTPException(status_code=400, detail="Document has insufficient text.")

    if GROQ_API_KEY:
        prompt = f"""
        Generate 3 high quality multiple choice questions from this text.
        Text:
        \"\"\"{extracted[:4000]}\"\"\"

        Return ONLY a JSON array:
        [
          {{
            "question": "Question text?",
            "options": ["A", "B", "C", "D"],
            "correct_idx": 0,
            "explanation": "Brief reason"
          }}
        ]
        """
        try:
            res = ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "You output raw JSON arrays only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            raw = res.choices[0].message.content.strip()
            clean = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
            questions = json.loads(clean)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
    else:
        # Fallback local regex parsing
        sentences = [s.strip() for s in re.split(r'\. |\n', extracted) if len(s.strip()) > 30]
        questions = []
        for idx, sentence in enumerate(sentences[:3]):
            words = sentence.split()
            snippet = " ".join(words[:min(10, len(words))])
            questions.append({
                "question": f"As per training manual: \"{snippet}...\", which provision applies?",
                "options": [f"Standard operational directive ({idx+1})", "Draft guideline", "Historical framework", "None of above"],
                "correct_idx": 0,
                "explanation": f"Mandated from curriculum: {sentence[:70]}..."
            })

    for q in questions:
        db.add(QuizQuestion(
            course_id=course_id,
            question=q["question"],
            options_json=json.dumps(q["options"]),
            correct_idx=int(q["correct_idx"]),
            explanation=q.get("explanation", "")
        ))
    db.commit()
    return {"message": f"Successfully added {len(questions)} questions to {course_id}!"}
