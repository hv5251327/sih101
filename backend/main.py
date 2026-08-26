import os
import io
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
from pypdf import PdfReader

app = FastAPI(title="MoSPI AI Skill Intelligence & iGOT Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

XAI_API_KEY = os.getenv("XAI_API_KEY", "your_xai_api_key_here")
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1"
)

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

@app.get("/")
def read_root():
    return {"status": "MoSPI Skill Intelligence Platform Running with Grok AI", "version": "3.0"}

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

@app.post("/api/ai/grok-quiz")
async def generate_quiz_with_grok(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    extracted_text = ""
    if file:
        file_bytes = await file.read()
        if file.filename.lower().endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                extracted_text += (page.extract_text() or "") + "\n"
        else:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")
    elif raw_text:
        extracted_text = raw_text
    else:
        raise HTTPException(status_code=400, detail="No document or text provided")

    context = extracted_text[:8000].strip()
    if not context:
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    prompt = f"""
    Analyze the following official training material and generate 3 high-quality multiple choice questions (MCQs) for statistical officers.
    Return ONLY a valid JSON array of objects with the exact schema:
    [
      {{
        "question": "Question text here",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_index": 0,
        "explanation": "Detailed explanation of why this option is correct."
      }}
    ]

    Training Material Context:
    {context}
    """

    try:
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert curriculum evaluator for the National Statistical Systems Training Academy (NSSTA). Output strictly valid JSON without Markdown wraps."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        response_content = response.choices[0].message.content.strip()
        if response_content.startswith("```json"):
            response_content = response_content[7:-3].strip()
        elif response_content.startswith("```"):
            response_content = response_content[3:-3].strip()

        quiz_data = json.loads(response_content)
        return {"status": "success", "quiz": quiz_data}
    except Exception as e:
        # Fallback simulated response if API key is not configured or fails
        return {
            "status": "fallback",
            "quiz": [
                {
                    "question": "According to the parsed curriculum, what is the primary protocol for minimizing non-sampling error in survey operations?",
                    "options": ["Total Survey Error (TSE) Methodology", "Uncalibrated Quota Sampling", "Arbitrary Imputation", "Exclusion of Metadata"],
                    "correct_index": 0,
                    "explanation": "TSE provides systematic quality assurance across data collection stages."
                },
                {
                    "question": "Which standard is mandated for official macroeconomic aggregation and national accounts compilation?",
                    "options": ["System of National Accounts (SNA 2008)", "Unweighted Raw Counts", "Ad-hoc Local Indexing", "Non-probabilistic Sampling"],
                    "correct_index": 0,
                    "explanation": "SNA 2008 is the international standard framework adopted by MoSPI."
                }
            ]
        }
