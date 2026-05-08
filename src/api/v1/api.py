# Location: /src/api/v1/api.py
from fastapi import APIRouter
from src.api.v1.endpoints import resumes

api_router = APIRouter()

# Include the resume endpoints
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])

# We can add more routers here later (e.g., /analytics)