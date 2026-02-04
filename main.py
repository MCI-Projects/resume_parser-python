import re
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Resume Parser API - Name Fix + Top 3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------ Utilities ------------------------

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_RANGE = rf"(?:{MONTHS}\s+\d{{4}}|\d{{4}})(?:\s*[-–]\s*(?:{MONTHS}\s+\d{{4}}|Present|\d{{4}}))?"

def clean_text(text: str) -> str:
    text = text.replace("•", "\n").replace("●", "\n").replace("·", "\n").replace("☒", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text

def split_lines(text: str) -> List[str]:
    return [l.strip() for l in text.split("\n") if l.strip()]

# ------------------------ Extraction helpers ------------------------

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

def extract_education(text: str) -> List[Dict[str, str]]:
    lines = split_lines(text)
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.search(r"(Bachelor|Diploma|Degree|Certificate)", line, re.IGNORECASE):
            qual = line
            inst, from_, to_ = "", "", ""
            # Look backward for institution
            if i > 0:
                prev = lines[i-1]
                if re.search(r"(University|Academy|Institute|College|Polytechnic|School|NTUC LearningHub)", prev, re.IGNORECASE):
                    inst = prev
            # Look forward for dates
            for j in range(i+1, min(i+3, len(lines))):
                m = re.search(rf"({MONTHS}\s+\d{{4}}|\d{{4}})\s*[-–]\s*({MONTHS}\s+\d{{4}}|Present|\d{{4}})", lines[j])
                if m:
                    from_, to_ = m.group(1), m.group(2)
                    break
            entries.append({
                "Qualification": qual,
                "Major_Department": "",
                "Institute_School": inst,
                "From": from_,
                "To": to_,
            })
        i += 1
    return entries

# ------------------------ Work Experience ------------------------

def extract_work_experience(text: str) -> List[Dict[str, str]]:
    lines = split_lines(text)
    entries = []
    current = None

    for i, l in enumerate(lines):
        # Match Job Title + Company patterns
        m = re.match(r"(?P<title>[A-Za-z &/]+)\s+[-–]?\s*(?P<company>[A-Za-z &]+)$", l)
        if m:
            if current:
                entries.append(current)
            current = {
                "Company": m.group("company").strip(),
                "Occupation_Job_Title": m.group("title").strip(),
                "From": "",
                "To": "",
                "Reason_For_Leaving": "",
                "Description": ""
            }
            continue

        # Match Dates
        m_dates = re.match(rf"({MONTHS}\s+\d{{4}}|\d{{4}})\s*[-–]\s*({MONTHS}\s+\d{{4}}|Present|\d{{4}})", l)
        if m_dates and current:
            current["From"], current["To"] = m_dates.group(1), m_dates.group(2)
            continue

        # Reason for leaving
        rm = re.search(r"Reason\s*for\s*leaving\s*[:\-]\s*(.+)", l, re.IGNORECASE)
        if rm and current:
            current["Reason_For_Leaving"] = rm.group(1).strip()
            continue

        # Description / bullets
        if current:
            desc = re.sub(r"^[\-\.\*•●·]\s*", "", l).strip()
            if desc:
                if current["Description"]:
                    current["Description"] += " " + desc
                else:
                    current["Description"] = desc

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
        return {"Name": "", "Email": "", "Mobile": "", "Date_of_Birth": "", "Gender": "", "Language": "", "Nationality": "", "NoticePeriod": "", "Race": "", "Skills": "", "Education": [], "WorkExperience": []}

    text = clean_text(text)
    education = extract_education(text)
    work_experience = extract_work_experience(text)

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
