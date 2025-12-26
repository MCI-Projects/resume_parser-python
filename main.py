import os
from fastapi import FastAPI, UploadFile, File
import pdfplumber
import docx
from supabase import create_client

# Supabase configuration using environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

@app.post("/upload")
async def upload_resume(resume: UploadFile = File(...)):
    text = ""

    # Extract text from PDF
    if resume.filename.endswith(".pdf"):
        with pdfplumber.open(resume.file) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
    
    # Extract text from DOCX
    elif resume.filename.endswith(".docx"):
        doc = docx.Document(resume.file)
        text = "\n".join([p.text for p in doc.paragraphs])
    
    else:
        return {"error": "Only PDF and DOCX files are allowed"}

    # Upload file to Supabase
    resume.file.seek(0)  # Reset file pointer
    supabase.storage.from_("resumes").upload(resume.filename, resume.file.read())

    # Dummy parsed data (you will replace with actual parsing later)
    data = {
        "Name": "John Doe",
        "Email": "john@example.com",
        "Phone": "+65 91234567",
        "Education_Subform": [{"Degree": "B.Tech", "Year": "2022"}],
        "WorkExperience_Subform": [{"Company": "ABC Corp", "Years": "2"}]
    }

    return data
