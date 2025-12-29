import re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Resume Parser API - Phase 1")

# Allow Zoho
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
            "Mobile": ""
        }

    # 🔑 RETURN ONLY SIMPLE JSON
    return {
        "Name": extract_name(text),
        "Email": extract_email(text),
        "Mobile": extract_phone(text)
    }
