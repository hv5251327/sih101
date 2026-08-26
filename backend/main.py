from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import re

app = FastAPI(title="MoSPI AI Skill Intelligence & iGOT Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Skill Competency Framework for MoSPI & Official Statistics
ROLE_FRAMEWORKS = {
    "Director General (Statistics)": {
        "required_skills": ["National Accounts", "SDG Indicators", "AI/ML Policy", "Strategic Leadership", "Metadata Standards"],
        "baseline_score": 90
    },
    "Deputy Director General (DDG)": {
        "required_skills": ["Survey Design", "National Accounts", "Data Quality Frameworks", "Big Data Analytics", "Project Management"],
        "baseline_score": 85
    },
    "Director / Joint Director (ISS)": {
        "required_skills": ["Sampling Theory", "Python", "R", "National Accounts", "Data Privacy & Governance"],
        "baseline_score": 80
    },
    "Deputy Director / Assistant Director (ISS)": {
        "required_skills": ["Survey Sampling", "Python", "R", "SQL", "Price Statistics", "Metadata Standards"],
        "baseline_score": 75
    },
    "Senior Statistical Officer (SSO)": {
        "required_skills": ["Field Data Collection", "SPSS", "Stata", "Labour Statistics", "Data Quality Frameworks", "Cybersecurity"],
        "baseline_score": 70
    },
    "Junior Statistical Officer (JSO)": {
        "required_skills": ["Data Validation", "Basic Python", "Excel/SPSS", "Agricultural Statistics", "Code of Ethics"],
        "baseline_score": 65
    }
}

class AssessmentRequest(BaseModel):
    designation: str
    known_skills: List[str]

class QuizGenerationRequest(BaseModel):
    content: str
    num_questions: Optional[int] = 3

@app.get("/")
def read_root():
    return {"status": "MoSPI Skill Intelligence Platform Running", "version": "2.0-AI"}

@app.post("/api/ai/skill-gap")
def compute_skill_gap(req: AssessmentRequest):
    framework = ROLE_FRAMEWORKS.get(req.designation, {
        "required_skills": ["Official Statistics Foundation", "Data Privacy", "Survey Design", "Ethics"],
        "baseline_score": 70
    })
    
    required = set(framework["required_skills"])
    known = set(req.known_skills)
    missing = list(required - known)
    
    match_pct = max(20, round((len(required & known) / len(required)) * 100)) if required else 50
    
    return {
        "designation": req.designation,
        "competency_score": match_pct,
        "target_baseline": framework["baseline_score"],
        "acquired_skills": list(known),
        "skill_gaps": missing,
        "recommended_priority": "High" if match_pct < framework["baseline_score"] else "Standard"
    }

@app.post("/api/ai/generate-quiz")
async def generate_quiz_from_content(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    extracted_text = ""
    if file:
        content_bytes = await file.read()
        extracted_text = content_bytes.decode("utf-8", errors="ignore")
    elif raw_text:
        extracted_text = raw_text
    else:
        extracted_text = "Official statistics provide quantitative or qualitative information on economy and society."

    # Heuristic NLP MCQ Generator
    words = re.findall(r'\b[A-Za-z]{4,}\b', extracted_text)
    primary_term = words[0] if words else "National Accounts"
    secondary_term = words[1] if len(words) > 1 else "Sampling Strategy"

    generated_questions = [
        {
            "id": 1,
            "question": f"In the context of the uploaded curriculum, what is the primary role of '{primary_term}' in statistical governance?",
            "options": [
                f"Standardizing data pipelines and enhancing reliability of {primary_term}",
                f"Eliminating sample weights without variance estimation",
                f"Replacing official metadata repositories",
                f"Restricting public microdata dissemination"
            ],
            "correct_index": 0,
            "explanation": f"{primary_term} acts as a key methodological foundation to ensure reliable and standardized data governance."
        },
        {
            "id": 2,
            "question": f"Which protocol ensures compliance during field execution for '{secondary_term}'?",
            "options": [
                "Total Survey Error (TSE) Minimization and Data Validation",
                "Arbitrary non-response imputation",
                "Uncalibrated quota sampling",
                "Exclusion of quality metrics"
            ],
            "correct_index": 0,
            "explanation": "TSE minimization and continuous validation ensure data integrity under NSSTA guidelines."
        }
    ]

    return {
        "status": "success",
        "processed_length": len(extracted_text),
        "quiz": generated_questions
    }

@app.get("/api/admin/analytics")
def get_analytics():
    return {
        "total_cadre_strength": 1420,
        "onboarded_officers": 890,
        "average_statistical_competency": "79.4%",
        "nssta_tpac_certifications_issued": 612,
        "domain_distribution": {
            "National Accounts & Price Statistics": 280,
            "Field Survey & Sampling Operations": 340,
            "AI/ML & Big Data Analytics": 150,
            "SDG & Metadata Governance": 120
        }
    }
