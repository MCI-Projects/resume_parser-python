import re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Resume Parser API - Full Version")

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
        r"\b(Python|Java|C\+\+|SQL|Excel|Communication|Leadership|AWS|Docker|React|Node\.js|Microsoft Office|MYOB|SQL Accounting)\b",
        text,
        re.IGNORECASE,
    )
    return ", ".join(set(skills)) if skills else ""

def extract_education(text):
    education_entries = []
    lines = text.split("\n")

    for line in lines:
        if not line.strip():
            continue

        match = re.match(
            r"(?P<qualification>[A-Za-z\(\)\s\.]+)"
            r"(?:\s*-\s*(?P<institute>[A-Za-z\s&\(\),]+))?"
            r"(?:\s*(?P<from>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{4}))?"
            r"\s*(?:[-–]\s*(?P<to>(?:Present|\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{4})))?",
            line.strip(),
            re.IGNORECASE,
        )

        if match:
            education_entries.append({
                "Qualification": (match.group("qualification") or "").strip(),
                "Major_Department": "",  # optional refinement
                "Institute_School": (match.group("institute") or "").strip(),
                "From": (match.group("from") or "").strip(),
                "To": (match.group("to") or "").strip(),
            })

    return education_entries

def extract_work_experience(text):
    work_entries = []
    lines = text.split("\n")

    current_entry = {}
    for line in lines:
        if not line.strip():
            continue

        # Match job line: "Human Resources Assistant Jan 2024 – Present"
        job_match = re.match(
            r"(?P<title>[A-Za-z\s/&]+)\s+(?P<from>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{4})"
            r"\s*[-–]\s*(?P<to>(?:Present|\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{4}))?",
            line.strip(),
            re.IGNORECASE,
        )

        if job_match:
            if current_entry:
                work_entries.append(current_entry)
                current_entry = {}

            current_entry = {
                "Company": "",
                "Occupation_Job_Title": (job_match.group("title") or "").strip(),
                "From": (job_match.group("from") or "").strip(),
                "To": (job_match.group("to") or "").strip(),
                "Reason_For_Leaving": "",
                "Description": ""
            }
            continue

        # Company line (usually above job title)
        if "PTE LTD" in line or "SDN BHD" in line or "Company" in line or "Services" in line:
            if current_entry and not current_entry.get("Company"):
                current_entry["Company"] = line.strip()
            else:
                current_entry = {
                    "Company": line.strip(),
                    "Occupation_Job_Title": "",
                    "From": "",
                    "To": "",
                    "Reason_For_Leaving": "",
                    "Description": ""
                }
            continue

        # Reason for leaving
        reason_match = re.search(r"Reason\s*for\s*Leaving:\s*(.*)", line, re.IGNORECASE)
        if reason_match and current_entry:
            current_entry["Reason_For_Leaving"] = reason_match.group(1).strip()
            continue

        # Description (bullet points)
        if current_entry:
            current_entry["Description"] += " " + line.strip()

    if current_entry:
        work_entries.append(current_entry)

    return work_entries

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
            "Skills": "",
            "Education": [],
            "WorkExperience": []
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
        "Education": extract_education(text),
        "WorkExperience": extract_work_experience(text)
    }