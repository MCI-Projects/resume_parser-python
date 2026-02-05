import re
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Resume Parser API - Full Extraction")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------ Utilities ------------------------

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|" \
         r"January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_RANGE = rf"(?:{MONTHS}\s+\d{{4}}|\d{{4}})(?:\s*[-–]\s*(?:{MONTHS}\s+\d{{4}}|Present|\d{{4}}))?"

def clean_text(text: str) -> str:
    text = text.replace("•", "\n").replace("●", "\n").replace("·", "\n").replace("☒", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text

def split_lines(text: str) -> List[str]:
    return [l.strip() for l in text.split("\n") if l.strip()]

# ------------------------ Field Extractors ------------------------

def extract_name(text: str) -> str:
    lines = split_lines(text)
    if not lines:
        return ""
    name_line = lines[0]
    if name_line.isupper():
        return " ".join(w.capitalize() for w in name_line.split())
    return name_line

def extract_email(text: str) -> str:
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return m.group(0) if m else ""

def extract_phone(text: str) -> str:
    m = re.search(r"(\+?\d[\d\s\-]{7,14})", text)
    return m.group(0).replace(" ", "") if m else ""

def extract_dob(text: str) -> str:
    m = re.search(r"\b(Date\s*of\s*Birth|DOB)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    return m.group(2).strip() if m else ""

def extract_gender(text: str) -> str:
    m = re.search(r"\b(Male|Female|Other)\b", text, re.IGNORECASE)
    return m.group(0).capitalize() if m else ""

def extract_language(text: str) -> str:
    m = re.search(r"Languages?\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    langs = re.findall(r"\b(English|Malay|Tamil|Mandarin|Hindi|French|Spanish|German)\b", text, re.IGNORECASE)
    return ", ".join(dict.fromkeys(w.upper() for w in langs)) if langs else ""

def extract_nationality(text: str) -> str:
    m = re.search(r"Nationality\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def extract_notice_period(text: str) -> str:
    m = re.search(r"Notice\s*Period\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def extract_race(text: str) -> str:
    m = re.search(r"Race\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def extract_skills(text: str) -> str:
    skills = re.findall(
        r"\b(Python|Java|SQL|Excel|Communication|Leadership|AWS|Docker|Recruiter|Talent|HR|Payroll|Onboarding|Change Management|MYOB|Info-Tech|Whyze|360 Recruiter|Candidate Placements)\b",
        text,
        re.IGNORECASE,
    )
    return ", ".join(dict.fromkeys(w.strip().capitalize() for w in skills)) if skills else ""

# ------------------------ Education ------------------------

def extract_education(lines: List[str]) -> List[Dict[str, str]]:
    entries = []
    for i, line in enumerate(lines):
        if re.search(r"(Bachelor|Diploma|Degree|Certificate|Certification)", line, re.IGNORECASE):
            inst = ""
            if i > 0 and re.search(r"(University|Academy|Institute|College|Polytechnic|School|NTUC LearningHub)", lines[i-1], re.IGNORECASE):
                inst = lines[i-1]
            entries.append({
                "Qualification": line,
                "Major_Department": "",
                "Institute_School": inst,
                "From": "",
                "To": ""
            })
    return entries

# ------------------------ Work Experience ------------------------

def extract_work_experience(lines: List[str]) -> List[Dict[str, str]]:
    entries = []
    current = None
    for i, line in enumerate(lines):
        # Match lines with a date range
        m_date = re.search(rf"({MONTHS}\s+\d{{4}}|\d{{4}})\s*[-–]\s*({MONTHS}\s+\d{{4}}|Present|\d{{4}})", line)
        if m_date:
            if current:
                entries.append(current)
            prev = lines[i-1].strip() if i > 0 else ""
            current = {
                "Company": prev if len(prev) < 50 else "",
                "Occupation_Job_Title": prev if len(prev) < 50 else line,
                "From": m_date.group(1),
                "To": m_date.group(2),
                "Reason_For_Leaving": "",
                "Description": ""
            }
        else:
            if current:
                desc = re.sub(r"^[\-\.\*•●·]\s*", "", line).strip()
                if desc:
                    current["Description"] += (" " if current["Description"] else "") + desc
    if current:
        entries.append(current)
    return entries

# ------------------------ API ------------------------

@app.post("/upload")
async def upload_resume(resume: UploadFile = File(...)):
    text = ""
    if resume.filename.lower().endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(resume.file) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    elif resume.filename.lower().endswith(".docx"):
        import docx
        doc = docx.Document(resume.file)
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        text = (await resume.read()).decode("utf-8", errors="ignore")

    text = clean_text(text)
    lines = split_lines(text)
    education = extract_education(lines)
    work_experience = extract_work_experience(lines)

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
        "Education": education[:3],           # top 3
        "WorkExperience": work_experience[:3] # top 3
    }
