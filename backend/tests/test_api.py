from fastapi.testclient import TestClient
import pymupdf

from app.main import app

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
