import os
import re
import random
from fastapi import FastAPI, UploadFile, File
from supabase import create_client
from fastapi.middleware.cors import CORSMiddleware

# --- Supabase configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FastAPI app ---
app = FastAPI(title="Resume Parser API")

# Enable CORS (allow Zoho or any origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to Zoho domains
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper functions ---
def extract_name(text):
    lines = text.split("\n")
    for line in lines:
        if len(line.split()) in [2, 3] and all(w[0].isupper() for w in line.split()):
            return line.strip()
    return "Not found"

def extract_email(text):
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0) if match else "Not found"

def extract_phone(text):
    match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\d{6,12})", text)
    return match.group(0) if match else "Not found"

def extract_education(text):
    edu_list = []
    degrees = ["B.Tech", "BE", "M.Tech", "ME", "MBA", "B.Sc", "M.Sc"]
    lines = text.split("\n")
    for line in lines:
        for deg in degrees:
            if deg in line:
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                edu_list.append({
                    "Degree": deg,
                    "Year": year_match.group(0) if year_match else ""
                })
    return edu_list

def extract_experience(text):
    exp_list = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "Company" in line or "Experience" in line:
            company = line.split(":")[-1].strip() if ":" in line else line
            years = "1"
            for j in range(i+1, min(i+4, len(lines))):
                y = re.search(r"(\d+)\s*years?", lines[j], re.I)
                if y:
                    years = y.group(1)
                    break
            exp_list.append({"Company": company, "Years": years})
    return exp_list

# --- API endpoint ---
@app.post("/upload")
async def upload_resume(resume: UploadFile = File(...)):
    text = ""

    # PDF extraction
    if resume.filename.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(resume.file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

    # DOCX extraction
    elif resume.filename.endswith(".docx"):
        import docx
        doc = docx.Document(resume.file)
        text = "\n".join([p.text for p in doc.paragraphs])

    else:
        return {"error": "Only PDF and DOCX files are allowed"}

    # Reset file pointer
    resume.file.seek(0)

    # Add 5-6 digit prefix to filename
    prefix = random.randint(10000, 999999)
    filename = f"{prefix}_{resume.filename}"

    # Upload to Supabase
    supabase.storage.from_("resumes").upload(filename, resume.file.read())

    # Get public URL
    public_url = supabase.storage.from_("resumes").get_public_url(filename)

    # Parsed data
    data = {
        "Name": extract_name(text),
        "Email": extract_email(text),
        "Phone": extract_phone(text),
        "Education_Subform": extract_education(text),
        "WorkExperience_Subform": extract_experience(text),
        "Resume_File": filename,
        "Resume_URL": public_url
    }

    return data
