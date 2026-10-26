from typing import Literal

from pydantic import BaseModel


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


class ResumeAnalysisResponse(BaseModel):
    filename: str
    file_type: Literal["PDF", "TXT"]
    extracted_text: str
    analysis_status: Literal["completed", "demo_mode", "not_connected"]
    message: str
    summary: str
    skills: list[str]
    experience: list[str]
    education: list[str]
    completeness: int
    highlights: list[str]
    analysis_level: str
    summary_style: str
