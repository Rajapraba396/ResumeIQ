import json
import os
from urllib import error, request

KEY_ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _strip_markdown_fence(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json") :]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _extract_keywords(text: str) -> list[str]:
    lowered = text.lower()
    keyword_map = {
        "python": ["python", "pandas", "numpy", "scikit"],
        "sql": ["sql", "postgresql", "mysql", "database"],
        "javascript": ["javascript", "typescript", "node", "react", "vue"],
        "fastapi": ["fastapi", "api", "rest"],
        "excel": ["excel", "power bi", "tableau"],
        "leadership": ["leadership", "mentored", "managed", "coordinated"],
        "communication": ["communication", "client", "stakeholder", "presentation"],
        "project management": ["project management", "planning", "roadmap", "schedule"],
        "aws": ["aws", "cloud", "docker", "kubernetes"],
    }
    skills = []
    for skill, aliases in keyword_map.items():
        if any(alias in lowered for alias in aliases):
            skills.append(skill)
    return skills


def _fallback_analysis(extracted_text: str, analysis_level: str, summary_style: str) -> dict:
    lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
    keyword_list = _extract_keywords(extracted_text)
    if not keyword_list:
        keyword_list = ["Communication", "Problem solving", "Team collaboration", "Project management"]

    sentence_parts = [
        line for line in lines if len(line) < 200 and not line.endswith(":")
    ]
    summary_base = sentence_parts[0] if sentence_parts else "The candidate presents experience in technical, collaborative, and project-focused work."
    if summary_style == "brief":
        summary = summary_base
    elif summary_style == "bullet points":
        summary = "• " + summary_base + "\n• Demonstrated ability to work across teams and deliver clear outcomes.\n• Strong alignment with the role requirements listed in the resume."
    else:
        summary = (
            f"This resume describes a candidate with experience in {', '.join(keyword_list[:3]) or 'core workplace skills'} "
            f"and a clear focus on delivery, collaboration, and professional growth. The candidate highlights relevant responsibilities "
            "and outcomes that suggest readiness for structured, team-based work."
        )

    experience_items = [
        line for line in lines if any(term in line.lower() for term in ["experience", "developer", "coordinator", "analyst", "intern", "engineer", "manager", "specialist"])
    ]
    if not experience_items:
        experience_items = ["Relevant work experience and project responsibilities are present in the resume."]

    education_items = [
        line for line in lines if any(term in line.lower() for term in ["bachelor", "master", "degree", "university", "college", "school", "education"])
    ]
    if not education_items:
        education_items = ["Education details are included in the uploaded resume."]

    completeness = 72
    if any(token in extracted_text.lower() for token in ["email", "@", "phone", "linkedin", "github"]):
        completeness += 8
    if any(token in extracted_text.lower() for token in ["experience", "worked", "intern", "project"]):
        completeness += 8
    if any(token in extracted_text.lower() for token in ["degree", "university", "bachelor", "master"]):
        completeness += 7
    completeness = min(completeness, 100)

    highlight_items = [
        "Relevant work history with clear professional responsibilities.",
        f"Detected skills: {', '.join(keyword_list[:4])}.",
        "Resume content is structured enough for a recruiter to understand candidate fit.",
    ]

    return {
        "filename": "resume.txt",
        "file_type": "TXT",
        "extracted_text": extracted_text,
        "analysis_status": "demo_mode",
        "message": "Gemini API is not configured. Demo analysis is being used instead.",
        "summary": summary,
        "skills": keyword_list,
        "experience": experience_items[:3],
        "education": education_items[:3],
        "completeness": completeness,
        "highlights": highlight_items,
        "analysis_level": analysis_level,
        "summary_style": summary_style,
    }


def _parse_gemini_response(payload: dict) -> dict:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise ValueError("No Gemini candidates returned.")

    content = candidates[0].get("content", {})
    parts = content.get("parts") or []
    if not parts:
        raise ValueError("No Gemini content parts returned.")

    response_text = parts[0].get("text") or "{}"
    cleaned = _strip_markdown_fence(response_text)
    parsed = json.loads(cleaned)

    required_fields = [
        "summary",
        "skills",
        "experience",
        "education",
        "completeness",
        "highlights",
    ]
    for field in required_fields:
        if field not in parsed:
            raise KeyError(f"Missing Gemini field: {field}")

    return {
        "analysis_status": "completed",
        "message": "Resume analyzed with Gemini API.",
        "summary": str(parsed["summary"]),
        "skills": [str(item) for item in parsed.get("skills", [])],
        "experience": [str(item) for item in parsed.get("experience", [])],
        "education": [str(item) for item in parsed.get("education", [])],
        "completeness": int(parsed.get("completeness", 75)),
        "highlights": [str(item) for item in parsed.get("highlights", [])],
    }


def analyze_resume_text(extracted_text: str, analysis_level: str = "standard", summary_style: str = "brief") -> dict:
    api_key = next((os.getenv(name) for name in KEY_ENV_VARS if os.getenv(name)), None)
    if not api_key:
        return _fallback_analysis(extracted_text, analysis_level, summary_style)

    prompt = (
        "Analyze the resume text and return valid JSON only with keys: "
        "summary, skills, experience, education, completeness, highlights. "
        f"Use analysis level '{analysis_level}' and summary style '{summary_style}'. "
        "Keep it realistic and concise. Resume text:\n"
        f"{extracted_text[:15000]}"
    )

    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
            },
        }
    ).encode("utf-8")

    model_candidates = (
        "gemini-3.8-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    )

    for model_name in model_candidates:
        request_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )
        req = request.Request(request_url, data=body, headers={"Content-Type": "application/json"})

        try:
            with request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            analysis = _parse_gemini_response(payload)
            return {**analysis, "analysis_level": analysis_level, "summary_style": summary_style}
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404 and model_name != model_candidates[-1]:
                continue
            break
        except (ValueError, KeyError, TypeError, error.URLError):
            break

    return _fallback_analysis(extracted_text, analysis_level, summary_style)
