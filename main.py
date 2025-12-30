import re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Resume Parser API - Phase 2")

# Allow all origins (you can restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helper functions ----------

def extract_name(text):
    lines = text.split("\n")
    for line in lines:
        words = line.strip().split()
        if 2 <= len(words) <= 4 and all(w[:1].isupper() for w in words):
            return line.strip()
    return ""

def extract_email(text):
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else ""

def extract_phone(text):
    match = re.search(r"(\+?\d[\d\s\-]{7,14})", text)
    return match.group(0) if match else ""

def extract_dob(text):
    match = re.search(
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
        text,
        re.IGNORECASE,
    )
    return match.group(0) if match else ""

def extract_gender(text):
    match = re.search(r"\b(Male|Female|Other)\b", text, re.IGNORECASE)
    return match.group(0).capitalize() if match else ""

def extract_language(text):
    match = re.search(r"Languages?:\s*(.*)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    langs = re.findall(
        r"\b(English|Hindi|Mandarin|French|Spanish|German|Tamil|Malay)\b",
        text,
        re.IGNORECASE,
    )
    return ", ".join(set(langs)) if langs else ""

def extract_nationality(text):
    match = re.search(r"Nationality:\s*(.*)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

def extract_notice_period(text):
    match = re.search(r"Notice\s*Period:\s*(.*)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

def extract_race(text):
    match = re.search(r"Race:\s*(.*)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

def extract_skills(text):
    match = re.search(r"Skills?:\s*(.*)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    skills = re.findall(
        r"\b(Python|Java|C\+\+|SQL|Excel|Communication|Leadership|AWS|Docker|React|Node\.js)\b",
        text,
        re.IGNORECASE,
    )
    return ", ".join(set(skills)) if skills else ""

# ---------- API ----------

@app.post("/upload")
async def upload_resume(resume: UploadFile = File(...)):
    text = ""

    # PDF
    if resume.filename.lower().endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(resume.file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

    # DOCX
    elif resume.filename.lower().endswith(".docx"):
        import docx
        doc = docx.Document(resume.file)
        text = "\n".join(p.text for p in doc.paragraphs)

    else:
        return {
            "Name": "",
            "Email": "",
            "Mobile": "",
            "Date_of_Birth": "",
            "Gender": "",
            "Language": "",
            "Nationality": "",
            "NoticePeriod": "",
            "Race": "",
            "Skills": ""
        }

    # 🔑 RETURN JSON
    return {
        "Name": extract_name(text),
        "Email": extract_email(text),
        "Mobile": extract_phone(text),
        "Date_of_Birth": extract_dob(text),
        "Gender": extract_gender(text),
        "Language": extract_language(text),
        "Nationality": extract_nationality(text),
        "NoticePeriod": extract_notice_period(text),
        "Race": extract_race(text),
        "Skills": extract_skills(text),
    }