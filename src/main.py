# Location: /src/main.py (Updated)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.db.session import engine
from src.db import models
from src.api.v1.api import api_router # We will create this file next

# This command creates the database tables if they don't exist
# It's okay for a hackathon. In production, we'd use Alembic.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Powered Resume Parser",
    version="1.0",
    description="Hackathon project for parsing resumes with AI."
)

@app.on_event("startup")
async def startup_event():
    # This is a good place for any startup logic
    print("--- API is starting up! ---")

# Allow the React dev server (Vite) to talk to this API.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check Endpoint ---
@app.get("/health", tags=["General"])
async def get_health():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok", "message": "API is healthy"}

# --- Include the v1 API routes ---
# All routes in api_router will be prefixed with /api/v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint.
    """
    return {"message": "Welcome to the AI Resume Parser API"}