# Location: /src/api/v1/endpoints/resumes.py

import shutil
import hashlib
import os
import uuid
import json
import time
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import Resume
from src.worker.tasks import parse_resume_task 

# --- NEW IMPORTS FOR THE /MATCH ENDPOINT ---
from src.core.config import settings
import google.generativeai as genai
from google.generativeai import types as genai_types
from pydantic import BaseModel
# -------------------------------------------

# --- IMPORT ALL OUR SCHEMAS ---
from src.api.v1.schemas import (
    ResumeDataResponse, 
    ResumeMetadata,
    MatchRequest,
    MatchResponse,
    MatchingResults,
    MatchExplanation,
    MatchMetadata,
    CategoryScores,
    SkillsMatchDetails,
    ExperienceMatchDetails,
    EducationMatchDetails,
    RoleAlignmentDetails,
    LocationMatchDetails,
    GapAnalysisItem,
    SalaryAlignment,
)
# ------------------------------

router = APIRouter()

# Use a project-relative uploads directory instead of a Docker-only path.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB

try:
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        gemini_match_model = genai.GenerativeModel(
            'gemini-2.5-pro',
            generation_config=genai_types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=MatchResponse, 
                temperature=0.1
            )
        )
        print("--- Gemini PRO model for MATCHING configured successfully ---")
    else:
        print("!!! WARNING: GEMINI_API_KEY is not set. /match endpoint will not work. !!!")
        gemini_match_model = None
except Exception as e:
    print(f"!!! CRITICAL: FAILED TO CONFIGURE GEMINI MATCH MODEL. {e} !!!")
    gemini_match_model = None
# =================================================


def get_gemini_match_prompt(resume_json: dict, job_json: dict) -> str:
    """
    Creates the master prompt to send to the Gemini API for matching.
    """
    prompt = f"""
    You are an expert **AI HR Analyst and Hiring Manager**. 
    
    Your task is to perform a detailed, quantitative analysis comparing the following candidate's RESUME to the provided JOB DESCRIPTION.

    **INSTRUCTIONS:**
    1.  **Analyze Both Inputs:** Read the structured JSON for the resume and the job description.
    2.  **Score Categories (0-100):** For each category (skills, experience, education, etc.), generate a score from 0-100.
    3.  **Calculate Overall Score:** Create a final, weighted "overallScore" based on your category scores.
    4.  **Provide Analysis:** Fill *all* fields, including `strengthAreas`, `gapAnalysis`, and `explanation`.
    5.  **Be Honest:** If the candidate is a poor fit, give a low score. If they are a strong fit, give a high score. Justify your reasoning.

    ---
    CANDIDATE'S RESUME (JSON):
    {json.dumps(resume_json, indent=2)}
    ---
    JOB DESCRIPTION (JSON):
    {json.dumps(job_json, indent=2)}
    ---
    
    Now, perform the full analysis and return the results as a single JSON object that strictly follows the required schema.
    """
    return prompt


def get_file_hash(file):
    """Calculates the SHA-256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    for chunk in iter(lambda: file.read(4096), b""):
        hash_sha256.update(chunk)  
    file.seek(0)
    return hash_sha256.hexdigest()

def save_upload_file(file: UploadFile, resume_id: uuid.UUID) -> str:
    """
    Saves the uploaded file to the UPLOAD_DIR using its resume_id as the filename.
    Returns the file path.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_extension = os.path.splitext(file.filename)[1]
    if not file_extension: # Handle cases like 'Resume' with no extension
        file_extension = ".dat" # Use a generic extension
        
    file_path = os.path.join(UPLOAD_DIR, f"{str(resume_id)}{file_extension}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
    return file_path

# -------------------------------------------


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Upload a resume file.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    if file.size > MAX_FILE_SIZE: 
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds 10MB limit. File size: {file.size / 1024 / 1024:.2f} MB"
        )

    file_hash = get_file_hash(file.file)
    
    existing_resume = db.query(Resume).filter(Resume.file_hash == file_hash).first()
    if existing_resume:
        raise HTTPException(
            status_code=400, 
            detail=f"Duplicate file. Resume already exists with ID: {existing_resume.id}"
        )

    new_resume = Resume(
        id=uuid.uuid4(),
        file_name=file.filename,
        file_size=file.size, 
        file_type=file.content_type,
        file_hash=file_hash,
        processing_status='pending'
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    try:
        saved_file_path = save_upload_file(file, new_resume.id)
        new_resume.file_path = saved_file_path 
        db.commit() 
    except Exception as e:
        print(f"Error saving file: {e}")
        new_resume.processing_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    parse_resume_task.delay(str(new_resume.id))
    print(f"Dispatched task for resume_id: {new_resume.id}")

    return {
        "id": new_resume.id,
        "status": new_resume.processing_status,
        "message": "Resume uploaded successfully, queued for processing.",
        "estimatedProcessingTime": 30 
    }

@router.get("/{id}", response_model=ResumeDataResponse)
async def get_parsed_resume(
    id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve the full, structured JSON data for a processed resume.
    """
    try:
        resume_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume ID format.")

    resume = db.query(Resume).filter(Resume.id == resume_uuid).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found") 
        
    if resume.processing_status != "completed":
        raise HTTPException(
            status_code=202, 
            detail=f"Resume processing is not complete. Current status: {resume.processing_status}"
        )
    
    ai_data = resume.structured_data or {}

    metadata = ResumeMetadata(
        fileName=resume.file_name,
        fileSize=resume.file_size,
        uploadedAt=resume.uploaded_at,
        processedAt=resume.processed_at,
        processingTime=(resume.processed_at - resume.uploaded_at).total_seconds() if resume.processed_at else None
    )

    response_data = ResumeDataResponse(
        id=resume.id,
        metadata=metadata,
        personalInfo=ai_data.get("personalInfo"),
        summary=ai_data.get("summary"),
        experience=ai_data.get("experience"),
        education=ai_data.get("education"),
        skills=ai_data.get("skills"),
        certifications=ai_data.get("certifications"),
        aiEnhancements=ai_data.get("aiEnhancements")
    )
    
    return response_data

@router.get("/{id}/status")
async def get_resume_status(
    id: str, 
    db: Session = Depends(get_db)
):
    """
    Get the processing status of a resume by its ID.
    """
    try:
        resume_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume ID format.")

    resume = db.query(Resume).filter(Resume.id == resume_uuid).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found") # <-- Fix 4.04 typo
        
    return {
        "id": resume.id,
        "status": resume.processing_status,
        "fileName": resume.file_name,
        "uploadedAt": resume.uploaded_at,
        "processedAt": resume.processed_at
    }

# --- THIS IS THE NEW "NICE-TO-HAVE" ENDPOINT ---

@router.post("/{id}/match", response_model=MatchResponse)
async def match_resume_to_job(
    id: str,
    match_request: MatchRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Compares a processed resume against a new job description
    and returns a detailed match analysis.
    """
    start_time = time.time()
    
    if not gemini_match_model:
        raise HTTPException(
            status_code=503, # 503 Service Unavailable
            detail="Gemini matching service is not configured. Check API key."
        )
        
    try:
        resume_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume ID format.")

    # 1. Get the resume data from our database
    resume = db.query(Resume).filter(Resume.id == resume_uuid).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.processing_status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Resume is not yet processed. Current status: {resume.processing_status}"
        )
    if not resume.structured_data:
        raise HTTPException(
            status_code=400,
            detail="Resume has no structured data to compare."
        )

    # 2. Get the job description from the user's request
    job_data = match_request.jobDescription.model_dump() # Convert Pydantic to dict

    # 3. Create the prompt and call the AI
    print("Sending Resume and Job Description to Gemini for matching...")
    try:
        prompt = get_gemini_match_prompt(resume.structured_data, job_data)
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold":"BLOCK_NONE"},
        ]
        
        response = gemini_match_model.generate_content(
            contents=prompt,
            safety_settings=safety_settings
        )
        
        # 4. Parse the AI's response
        # The AI is forced to return JSON, so we can parse it directly
        ai_response_json = json.loads(response.text)
        
        # 5. Add our own metadata and return the full response
        processing_time = time.time() - start_time
        
        # We manually add the last few fields that the AI doesn't know
        ai_response_json["resumeId"] = resume.id
        ai_response_json["jobTitle"] = job_data.get("title", "N/A")
        ai_response_json["company"] = job_data.get("company", "N/A")
        ai_response_json["metadata"] = {
            "matchedAt": datetime.now().isoformat(),
            "processingTime": processing_time,
            "algorithm": "Gemini 2.5 Pro - Structured Output",
            "confidenceFactors": {
                "dataCompleteness": 0.95, # Placeholder
                "skillExtraction": 0.90, # Placeholder
            }
        }

        # Validate our final object against the MatchResponse schema
        final_response = MatchResponse.model_validate(ai_response_json)
        
        print(f"--- [MATCH_SUCCESS] Job match complete in {processing_time:.2f}s ---")
        return final_response

    except Exception as e:
        print(f"[MATCH_FAILED] Error during matching: {e}")
        raise HTTPException(status_code=500, detail=f"AI matching failed: {e}")