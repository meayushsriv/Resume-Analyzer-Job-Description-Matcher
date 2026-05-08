# Location: /src/worker/tasks.py

import time
import datetime
import uuid
import os
import json
from typing import List, Dict, Optional # <-- This is correct

# --- AI IMPORTS ---
import google.generativeai as genai
from google.generativeai import types as genai_types
from src.core.config import settings

# --- PARSING LIBRARIES ---
import pdfplumber 
import docx

# --- OCR IMPORTS ---
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
# ------------------------

from src.worker.celery_app import celery_app
from src.db.session import SessionLocal
from src.db.models import Resume

# --- IMPORT THE PYDANTIC SCHEMAS ---
# We ONLY need BaseModel here now
from pydantic import BaseModel 
# ---------------------------------

# --- CONFIGURE THE GEMINI CLIENT ---
try:
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # --- THIS IS THE FIX ---
        # We are removing the complex generation_config that was
        # crashing the app. We will just initialize the model.
        gemini_model = genai.GenerativeModel('gemini-2.5-pro')
        # ---------------------------------
        
        print("--- Gemini PRO model configured successfully ---")
    else:
        print("!!! WARNING: GEMINI_API_KEY is not set. AI extraction will be skipped. !!!")
        gemini_model = None
except Exception as e:
    print(f"!!! CRITICAL: FAILED TO CONFIGURE GEMINI API. {e} !!!")
    gemini_model = None

# --- HELPER FUNCTIONS (UNCHANGED) ---

def ocr_pdf(file_path: str) -> str:
    """Extracts text from a scanned/image-based PDF using Tesseract OCR."""
    print(f"Running OCR on PDF: {file_path}")
    try:
        images = convert_from_path(file_path, poppler_path=None)
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img) + "\n"
        print(f"OCR extraction successful, {len(full_text)} chars.")
        return full_text
    except Exception as e:
        print(f"Error during OCR: {e}")
        raise

def parse_pdf(file_path: str) -> str:
    """Tries fast text extraction first, then falls back to slow OCR."""
    print(f"Parsing PDF: {file_path}")
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        if len(text.strip()) < 10: 
            print("No text found. Assuming scanned PDF. Falling back to OCR...")
            text = ocr_pdf(file_path)
        else:
            print(f"Text-based PDF extraction successful, {len(text)} chars.")
        
        return text
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        try:
            print("pdfplumber failed. Trying OCR as a last resort...")
            text = ocr_pdf(file_path)
            return text
        except Exception as ocr_e:
            print(f"Both text extraction and OCR failed: {ocr_e}")
            raise ocr_e

def parse_docx(file_path: str) -> str:
    print(f"Parsing DOCX: {file_path}")
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
        print(f"DOCX extraction successful, {len(text)} chars.")
        return text
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        raise

def parse_txt(file_path: str) -> str:
    print(f"Parsing TXT: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"TXT extraction successful, {len(text)} chars.")
        return text
    except Exception as e:
        print(f"Error parsing TXT: {e}")
        raise

def parse_image(file_path: str) -> str:
    """
    Extracts text from a single image file (JPG, PNG) using Tesseract OCR.
    """
    print(f"Running OCR on Image: {file_path}")
    try:
        img = Image.open(file_path)
        full_text = pytesseract.image_to_string(img) + "\n"
        print(f"Image OCR extraction successful, {len(full_text)} chars.")
        return full_text
    except Exception as e:
        print(f"Error during Image OCR: {e}")
        raise

# --- AI PROMPT ENGINEERING ---

def get_gemini_extraction_prompt(raw_text: str) -> str:
    """
    Creates the master prompt to send to the Gemini API.
    """
    
    # --- THIS IS THE FIX ---
    # We put the full, detailed JSON template *back into the prompt*.
    # This is the most reliable way to get the format we want.
    json_format_template = """
    {
      "personalInfo": {
        "name": { "first": "John", "last": "Doe", "full": "John Doe" },
        "contact": {
          "email": "john.doe@example.com",
          "phone": "+1-555-123-4567",
          "address": { "city": "San Francisco", "state": "CA", "country": "USA" },
          "linkedin": "https.linkedin.com/in/johndoe"
        }
      },
      "summary": {
        "text": "Experienced software engineer with 5+ years...",
        "careerLevel": "mid-level"
      },
      "experience": [
        {
          "title": "Senior Software Engineer",
          "company": "Tech Corp",
          "location": "San Francisco, CA",
          "startDate": "2021-03-01",
          "endDate": "2025-09-01",
          "description": "Led development of microservices...",
          "technologies": ["Python", "Docker", "AWS"]
        }
      ],
      "education": [
        {
          "degree": "Bachelor of Science",
          "field": "Computer Science",
          "institution": "University of California, Berkeley",
          "graduationDate": "2018-05-15"
        }
      ],
      "skills": {
        "technical": [
          {
            "category": "Programming Languages",
            "items": ["Python", "JavaScript", "Java", "Go"]
          },
          {
            "category": "Frameworks",
            "items": ["Django", "React", "Node.js"]
          }
        ],
        "soft": ["Leadership", "Communication", "Problem Solving"],
        "languages": [
          {
            "language": "English",
            "proficiency": "Native"
          }
        ]
      },
      "certifications": [
         {
           "name": "AWS Certified Solutions Architect",
           "issuer": "Amazon Web Services",
           "issueDate": "2023-06-15"
         }
      ],
      "aiEnhancements": {
        "qualityScore": 87,
        "completenessScore": 92,
        "suggestions": [
          "Add quantifiable achievements to work experience",
          "Include relevant technical certifications"
        ],
        "industryFit": {
          "software_engineering": 0.95,
          "data_science": 0.45,
          "product_management": 0.25
        },
        "careerProgressionAnalysis": "Candidate shows fast career growth; ready for senior role."
      }
    }
    """
    
    # The prompt instructs the AI for both extraction and analysis
    prompt = f"""
    You are an expert **AI HR Analyst and Senior Resume Parser**. 
    
    Your task is not just to extract text, but to provide a comprehensive analysis.

    **INSTRUCTIONS:**
    1. **Extraction (Mandatory):** Accurately extract all structured data from the resume text.
    2. **Analysis (Mandatory):** Fill the 'aiEnhancements' block completely, using logical deduction.
       - **qualityScore:** Judge the resume on a scale of 0-100 based on completeness and professionalism.
       - **completenessScore:** Calculate the percentage of core fields (Name, Email, 1 Experience, 1 Education) that were successfully extracted.
       - **industryFit:** Classify the candidate into 3 relevant industries (e.g., 'software_engineering', 'data_science') and provide a confidence score (0.0 to 1.0).
       - **careerProgressionAnalysis:** Briefly analyze the candidate's job history and offer one sentence of insight.

    You MUST return the output *only* as a single, valid JSON object following the JSON FORMAT TEMPLATE.
    Do not include any text, markdown (like ```json), or explanations before or after the JSON block.
    
    JSON FORMAT TEMPLATE:
    {json_format_template}
    
    ---
    RESUME TEXT TO PARSE:
    {raw_text}
    ---
    
    Now, parse the resume text and provide the output in the requested JSON format.
    Fill the fields accurately based on the candidate's content.
    If a field is not found, return null or an empty list [].
    """
    return prompt


# --- THE MAIN TASK ---

@celery_app.task
def parse_resume_task(resume_id_str: str):
    """
    This background task now does:
    1. Text extraction (PDF, DOCX, TXT, Images)
    2. AI-powered JSON parsing (using Gemini Pro)
    """
    print(f"--- [TASK_STARTED] for resume_id: {resume_id_str} ---")
    db = SessionLocal()
    file_name = "Unknown" 
    
    try:
        resume_id = uuid.UUID(resume_id_str)
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        file_name = resume.file_name if resume else "Unknown"

        if not resume:
            print(f"[TASK_ERROR] Resume with id {resume_id_str} not found.")
            return f"Failed: Resume {resume_id_str} not found"
        if not resume.file_path or not os.path.exists(resume.file_path):
            print(f"[TASK_ERROR] File not found at path: {resume.file_path}")
            raise Exception("File not found on server.")

        resume.processing_status = "processing"
        db.commit()

        # --- STEP A: REAL TEXT EXTRACTION (NOW WITH OCR) ---
        raw_text = ""
        file_type = resume.file_type.lower()
        print(f"Dispatching task for file type: {file_type}")
        
        if 'pdf' in file_type:
            raw_text = parse_pdf(resume.file_path)
        elif 'word' in file_type or 'officedocument' in file_type:
            raw_text = parse_docx(resume.file_path)
        elif 'text' in file_type:
            raw_text = parse_txt(resume.file_path)
        elif 'jpeg' in file_type or 'png' in file_type:
            raw_text = parse_image(resume.file_path)
        else:
            raise Exception(f"Unsupported file type: {file_type}")
        
        resume.raw_text = raw_text
        
        # --- STEP B: AI JSON EXTRACTION (Simplified Call) ---
        if not gemini_model:
            print("!!! WARNING: Gemini model not configured. Skipping AI extraction. !!!")
            extracted_json = {"error": "AI model not configured."}
        else:
            print(f"Sending {len(raw_text)} chars to Gemini PRO for extraction...")
            
            if len(raw_text.strip()) < 10:
                print("[TASK_WARNING] Skipping AI call due to empty extracted text.")
                extracted_json = {"error": "No text could be extracted from the document."}
            else:
                extraction_prompt = get_gemini_extraction_prompt(raw_text)
                
                # --- FIX 6: Simplified API call config ---
                generation_config = genai_types.GenerationConfig(
                    temperature=0.1 
                )
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold":"BLOCK_NONE"},
                ]
                
                response = gemini_model.generate_content(
                    contents=extraction_prompt,
                    generation_config=generation_config, # Pass config here
                    safety_settings=safety_settings
                )
                
                ai_response_text = response.text.strip().replace("```json", "").replace("```", "")
                extracted_json = json.loads(ai_response_text)
                
                print("--- [AI_SUCCESS] Gemini extraction complete ---")

        # --- STEP C: SAVE RESULTS ---
        resume.processing_status = "completed"
        resume.processed_at = datetime.datetime.now(datetime.timezone.utc)
        resume.structured_data = extracted_json 
        db.commit()
        
        print(f"--- [TASK_COMPLETED] for {resume.file_name} ---")
        return f"Successfully processed {resume.file_name}"

    except Exception as e:
        print(f"[TASK_FAILED] Error processing {resume_id_str}: {e}")
        db.rollback() 
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if resume:
            resume.processing_status = "failed"
            db.commit()
        return f"Failed to process {file_name}"
            
    finally:
        db.close()