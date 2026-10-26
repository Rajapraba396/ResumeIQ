from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.schemas.resume import (
    ResumeAnalysisRequest,
    ResumeAnalysisResponse,
    ResumeExtractionResponse,
    ResumeTextExtractionResponse,
)
from app.services.gemini_service import (
    GeminiAnalysisError,
    GeminiRequestError,
    InvalidGeminiResponseError,
    analyze_resume_text,
)
from app.services.pdf_service import (
    InvalidResumeFileError,
    NoSelectableTextError,
    extract_pdf_text,
    extract_txt_text,
)

router = APIRouter(prefix="/api", tags=["analysis"])
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
UPLOAD_READ_CHUNK_SIZE = 64 * 1024
ALLOWED_EXTENSIONS = {"pdf", "txt"}


async def _extract_uploaded_resume(file: UploadFile) -> tuple[str, str, str]:
    filename = file.filename or ""
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""

    try:
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and TXT files are supported.",
            )

        content = bytearray()
        while True:
            remaining_limit = MAX_UPLOAD_SIZE + 1 - len(content)
            chunk = await file.read(min(UPLOAD_READ_CHUNK_SIZE, remaining_limit))
            if not chunk:
                break

            content.extend(chunk)
            if len(content) > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="The uploaded file exceeds the 5 MB limit.",
                )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty.",
            )

        try:
            if extension == "txt":
                txt_bytes = bytes(content)
                try:
                    decoded = txt_bytes.decode("utf-8-sig")
                except UnicodeDecodeError as error:
                    raise InvalidResumeFileError("TXT files must use UTF-8 encoding.") from error
                if not decoded.strip():
                    raise InvalidResumeFileError("TXT files must use UTF-8 encoding.")
                extracted_text = extract_txt_text(txt_bytes)
            else:
                extracted_text = extract_pdf_text(bytes(content))
        except NoSelectableTextError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        except InvalidResumeFileError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

        if not extracted_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No text was found in the uploaded file.",
            )

        return filename, extension.upper(), extracted_text
    finally:
        await file.close()


@router.post(
    "/resumes/extract",
    response_model=ResumeTextExtractionResponse,
    summary="Extract text from a PDF or TXT resume",
)
async def extract_resume(file: UploadFile = File(...)) -> ResumeTextExtractionResponse:
    filename, file_type, text = await _extract_uploaded_resume(file)

    return ResumeTextExtractionResponse(
        filename=filename,
        file_type=file_type,
        character_count=len(text),
        text=text,
    )


@router.post(
    "/resumes/analyze",
    response_model=ResumeAnalysisResponse,
    summary="Analyze extracted resume text using Gemini or an explicitly labelled demo",
)
async def analyze_resume(request: ResumeAnalysisRequest) -> ResumeAnalysisResponse:
    try:
        analysis = await run_in_threadpool(
            analyze_resume_text,
            request.filename,
            request.text,
            request.analysis_level,
            request.summary_style,
        )
    except InvalidGeminiResponseError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except GeminiRequestError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except GeminiAnalysisError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    analysis["file_type"] = "PDF" if request.filename.lower().endswith(".pdf") else "TXT"
    return ResumeAnalysisResponse(**analysis)


@router.post(
    "/analyze",
    response_model=ResumeExtractionResponse,
    summary="Legacy analyze endpoint retained for compatibility",
)
async def legacy_analyze_resume(file: UploadFile = File(...)) -> ResumeExtractionResponse:
    filename, file_type, extracted_text = await _extract_uploaded_resume(file)

    return ResumeExtractionResponse(
        filename=filename,
        file_type=file_type,
        extracted_text=extracted_text,
        analysis_status="not_connected",
        message="Text extraction completed. AI analysis is not connected yet.",
    )
