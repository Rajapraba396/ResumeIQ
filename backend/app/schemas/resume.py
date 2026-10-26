from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ResumeExtractionResponse(BaseModel):
    filename: str
    file_type: Literal["PDF", "TXT"]
    extracted_text: str
    analysis_status: Literal["not_connected"]
    message: str


class ResumeTextExtractionResponse(BaseModel):
    filename: str
    file_type: Literal["PDF", "TXT"]
    character_count: int
    text: str


class ResumeAnalysisRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=50000)
    analysis_level: Literal["Basic", "Standard", "Detailed"] = "Standard"
    summary_style: Literal["Brief", "Detailed", "Bullet Points"] = "Brief"

    @field_validator("filename", "text")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field must not be blank.")
        return value.strip()


class ResumeAnalysisResponse(BaseModel):
    filename: str
    file_type: Literal["PDF", "TXT"]
    analysis_status: Literal["completed", "demo_mode"]
    message: str
    summary: str
    candidate_name: str | None
    contact_details: list[str]
    technical_skills: list[str]
    soft_skills: list[str]
    skills: list[str]
    internships: list[str]
    work_experience: list[str]
    experience: list[str]
    education: list[str]
    projects: list[str]
    certifications: list[str]
    achievements: list[str]
    missing_information: list[str]
    improvement_suggestions: list[str]
    completeness: int
    highlights: list[str]
    analysis_level: str
    summary_style: str
