from types import SimpleNamespace

from fastapi.testclient import TestClient
import pymupdf

from app.main import app
from app.routes import analysis as analysis_route
from app.services import gemini_service

client = TestClient(app)
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def make_pdf(text: str | None = None) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    if text is not None:
        page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def test_health_check_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "ResumeIQ API",
    }


def test_extract_returns_text_and_metadata_for_utf8_txt_with_bom() -> None:
    text = "Taylor Reed\nOperations Coordinator"
    response = client.post(
        "/api/resumes/extract",
        files={
            "file": (
                "resume.txt",
                b"\xef\xbb\xbf" + text.encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "resume.txt",
        "file_type": "TXT",
        "character_count": len(text),
        "text": text,
    }


def test_extract_returns_text_from_pdf() -> None:
    text = "Taylor Reed - Resume\n"
    response = client.post(
        "/api/resumes/extract",
        files={"file": ("resume.pdf", make_pdf(text.rstrip()), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "resume.pdf",
        "file_type": "PDF",
        "character_count": len(text),
        "text": text,
    }


def test_extract_rejects_unsupported_file_extension() -> None:
    response = client.post(
        "/api/resumes/extract",
        files={
            "file": (
                "resume.docx",
                b"not a supported file",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF and TXT files are supported."


def test_extract_rejects_empty_files() -> None:
    response = client.post(
        "/api/resumes/extract",
        files={"file": ("resume.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is empty."


def test_extract_rejects_files_over_five_megabytes() -> None:
    response = client.post(
        "/api/resumes/extract",
        files={
            "file": (
                "resume.txt",
                b"x" * (MAX_UPLOAD_SIZE + 1),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "The uploaded file exceeds the 5 MB limit."


def test_extract_rejects_corrupted_pdf() -> None:
    response = client.post(
        "/api/resumes/extract",
        files={"file": ("resume.pdf", b"not a PDF document", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded PDF could not be read."


def test_extract_rejects_txt_with_invalid_utf8() -> None:
    response = client.post(
        "/api/resumes/extract",
        files={"file": ("resume.txt", b"\xff\xfe", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "TXT files must use UTF-8 encoding."


def test_extract_returns_422_for_pdf_without_selectable_text() -> None:
    response = client.post(
        "/api/resumes/extract",
        files={
            "file": (
                "scanned-resume.pdf",
                make_pdf(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert "OCR may be required" in response.json()["detail"]


def test_legacy_analyze_endpoint_remains_available() -> None:
    response = client.post(
        "/api/analyze",
        files={"file": ("resume.txt", b"Taylor Reed", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["extracted_text"] == "Taylor Reed"


def test_analyze_returns_explicit_rule_based_demo_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    text = (
        "Taylor Reed\n"
        "taylor@example.com | 555-555-1234\n"
        "Python, SQL, communication\n"
        "Experience\n"
        "Operations Coordinator | 2022 - Present\n"
        "Education\n"
        "Bachelor of Arts, State University"
    )

    response = client.post(
        "/api/resumes/analyze",
        json={"filename": "taylor.txt", "text": text},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["filename"] == "taylor.txt"
    assert result["analysis_status"] == "demo_mode"
    assert "DEMO MODE" in result["message"]
    assert "not AI-generated" in result["message"]
    assert result["candidate_name"] == "Taylor Reed"
    assert result["contact_details"] == ["taylor@example.com", "555-555-1234"]
    assert "Python" in result["technical_skills"]
    assert "Communication" in result["soft_skills"]
    assert result["education"]
    assert result["work_experience"]
    assert isinstance(result["projects"], list)
    assert isinstance(result["missing_information"], list)
    assert isinstance(result["improvement_suggestions"], list)


def test_analyze_rejects_missing_or_blank_text() -> None:
    missing = client.post(
        "/api/resumes/analyze",
        json={"filename": "resume.txt"},
    )
    blank = client.post(
        "/api/resumes/analyze",
        json={"filename": "resume.txt", "text": "  \n"},
    )

    assert missing.status_code == 422
    assert blank.status_code == 422
    assert "text" in str(blank.json()["detail"])


def test_analyze_reports_invalid_gemini_response(monkeypatch) -> None:
    def invalid_response(*args, **kwargs):
        raise gemini_service.InvalidGeminiResponseError("Gemini returned an invalid analysis response.")

    monkeypatch.setattr(analysis_route, "analyze_resume_text", invalid_response)
    response = client.post(
        "/api/resumes/analyze",
        json={"filename": "resume.txt", "text": "Candidate resume text"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Gemini returned an invalid analysis response."


def test_analyze_reports_gemini_api_failure(monkeypatch) -> None:
    def api_failure(*args, **kwargs):
        raise gemini_service.GeminiRequestError("Gemini API request failed.")

    monkeypatch.setattr(analysis_route, "analyze_resume_text", api_failure)
    response = client.post(
        "/api/resumes/analyze",
        json={"filename": "resume.txt", "text": "Candidate resume text"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Gemini API request failed."


def test_gemini_service_uses_official_sdk_and_supported_model(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    parsed = gemini_service.ResumeAnalysisData(
        summary="Experienced software developer.",
        candidate_name="Taylor Reed",
        contact_details=["taylor@example.com"],
        technical_skills=["Python"],
        soft_skills=["Communication"],
        education=["Bachelor of Science"],
        internships=[],
        work_experience=["Software Developer, 2022-present"],
        projects=["ResumeIQ"],
        certifications=[],
        achievements=[],
        missing_information=[],
        improvement_suggestions=["Add measurable outcomes."],
        completeness=90,
    )
    calls = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(parsed=parsed, text=None)

    class FakeClient:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.models = FakeModels()

    monkeypatch.setattr(gemini_service.genai, "Client", FakeClient)
    result = gemini_service.analyze_resume_text("taylor.txt", "Taylor Reed resume text")

    assert calls["api_key"] == "test-key"
    assert calls["model"] == "gemini-3.8-flash"
    assert calls["config"].response_mime_type == "application/json"
    assert result["analysis_status"] == "completed"
    assert result["technical_skills"] == ["Python"]
    assert result["projects"] == ["ResumeIQ"]


def test_gemini_service_retries_transient_failure_with_exponential_backoff(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    parsed = gemini_service.ResumeAnalysisData(
        summary="Experienced software developer.",
        candidate_name="Taylor Reed",
        contact_details=[],
        technical_skills=["Python"],
        soft_skills=[],
        education=[],
        internships=[],
        work_experience=[],
        projects=[],
        certifications=[],
        achievements=[],
        missing_information=[],
        improvement_suggestions=[],
        completeness=50,
    )
    calls = {"count": 0}
    delays = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["count"] += 1
            if calls["count"] < 3:
                raise gemini_service.errors.APIError(
                    503,
                    {"error": {"message": "Service temporarily unavailable."}},
                )
            return SimpleNamespace(parsed=parsed, text=None)

    class FakeClient:
        def __init__(self, *, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_service.genai, "Client", FakeClient)
    monkeypatch.setattr(gemini_service.time, "sleep", delays.append)

    result = gemini_service.analyze_resume_text("resume.txt", "Taylor Reed resume")

    assert calls["count"] == 3
    assert delays == [1, 2]
    assert result["analysis_status"] == "completed"


def test_gemini_service_uses_labelled_demo_after_transient_retries(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    calls = {"count": 0}
    delays = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["count"] += 1
            raise gemini_service.errors.APIError(
                503,
                {"error": {"message": "Service temporarily unavailable."}},
            )

    class FakeClient:
        def __init__(self, *, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_service.genai, "Client", FakeClient)
    monkeypatch.setattr(gemini_service.time, "sleep", delays.append)

    result = gemini_service.analyze_resume_text("resume.txt", "Taylor Reed Python")

    assert calls["count"] == gemini_service.GEMINI_MAX_RETRIES + 1
    assert delays == [1, 2, 4]
    assert result["analysis_status"] == "demo_mode"
    assert "DEMO MODE" in result["message"]
    assert "not AI-generated" in result["message"]
    assert result["technical_skills"] == ["Python"]


def test_gemini_service_retries_only_temporary_http_statuses() -> None:
    for code in (408, 429, 500, 503, 599):
        assert gemini_service._is_retryable_api_error(
            gemini_service.errors.APIError(code, {"error": {"message": "Temporary failure"}})
        )

    for code in (400, 401, 403, 404):
        assert not gemini_service._is_retryable_api_error(
            gemini_service.errors.APIError(code, {"error": {"message": "Permanent failure"}})
        )


def test_gemini_service_explains_invalid_api_key_without_exposing_it(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-private-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    calls = {"count": 0}
    delays = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["count"] += 1
            raise gemini_service.errors.APIError(
                400,
                {
                    "error": {
                        "message": "API key not valid. Please pass a valid API key.",
                        "status": "INVALID_ARGUMENT",
                    }
                },
            )

    class FakeClient:
        def __init__(self, *, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_service.genai, "Client", FakeClient)
    monkeypatch.setattr(gemini_service.time, "sleep", delays.append)

    try:
        gemini_service.analyze_resume_text("resume.txt", "Resume text")
    except gemini_service.GeminiRequestError as error:
        assert "Google AI Studio" in str(error)
        assert "fake-private-key" not in str(error)
        assert calls["count"] == 1
        assert delays == []
    else:
        raise AssertionError("Invalid Gemini credentials should raise a clear error.")
