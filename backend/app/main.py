from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.analysis import router as analysis_router

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(
    title="ResumeIQ API",
    description="Backend API for the ResumeIQ resume analysis platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://resumeiq-frontend-1df9.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(analysis_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ResumeIQ API",
    }
