import os
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import docx
from supabase import create_client

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# Enable CORS so your widget/HTML can call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your domain if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_resume(resume: UploadFile = File(...)):
    try:
        # Extract text
        text = ""
        resume.file.seek(0)
        if resume.filename.endswith(".pdf"):
            with pdfplumber.open(resume.file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif resume.filename.endswith(".docx"):
            resume.file.seek(0)
            doc = docx.Document(resume.file)
            text = "\n".join([p.text for p in doc.paragraphs])
        else:
            return JSONResponse({"error": "Only PDF and DOCX files are allowed"}, status_code=400)

        # Upload file to Supabase
        resume.file.seek(0)
        supabase.storage.from_("resumes").upload(resume.filename, resume.file.read())

        # Parse Name (assume first line)
        lines = text.strip().split("\n")
        name = lines[0].strip() if lines else ""

        # Parse Email
        email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", text)
        email = email_match.group(0) if email_match else ""

        # Parse Phone (simple international format)
        phone_match = re.search(r"\+?\d[\d\s\-]{7,}\d", text)
        phone = phone_match.group(0) if phone_match else ""

        # Parse Education
        education = []
        for line in text.split("\n"):
            if re.search(r"(B\.Tech|M\.Tech|B\.Sc|M\.Sc|MBA|BA|MA)", line):
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                year = year_match.group(0) if year_match else ""
                education.append({"Degree": line.strip(), "Year": year})

        # Parse Work Experience
        work_experience = []
        for line in text.split("\n"):
            if re.search(r"(at\s[A-Z][a-zA-Z]+|Inc|Corp|LLC)", line):
                years_match = re.search(r"\b\d+\s?(years|yrs)\b", line.lower())
                years = years_match.group(0) if years_match else ""
                work_experience.append({"Company": line.strip(), "Years": years})

        # Return parsed data
        data = {
            "Name": name,
            "Email": email,
            "Phone": phone,
            "Education_Subform": education,
            "WorkExperience_Subform": work_experience
        }

        return JSONResponse(content=data)

    except Exception as e:
        print(e)
        return JSONResponse({"error": str(e)}, status_code=500)
