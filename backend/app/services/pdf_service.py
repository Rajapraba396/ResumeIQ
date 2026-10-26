import pymupdf


class InvalidResumeFileError(ValueError):
    """Raised when an uploaded PDF or TXT file cannot be read."""


class NoSelectableTextError(ValueError):
    """Raised when a valid PDF contains no selectable text."""


def _is_pdf_bytes(data: bytes) -> bool:
    if not data:
        return False
    return data.startswith(b"%PDF") or b"%PDF" in data[:1024]


def _is_utf8_text(data: bytes) -> bool:
    if not data:
        return False
    try:
        data.decode("utf-8-sig")
        return True
    except UnicodeDecodeError:
        return False


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract selectable text from every page of a PDF document.

    Raises:
        InvalidResumeFileError: If the PDF is invalid, encrypted, or unreadable.
        NoSelectableTextError: If the PDF has no selectable text. Scanned
            documents may require OCR, which this service does not perform.
    """
    if not _is_pdf_bytes(pdf_bytes):
        raise InvalidResumeFileError("The uploaded PDF could not be read.")

    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError, OSError) as error:
        raise InvalidResumeFileError("The uploaded PDF could not be read.") from error

    with document:
        if document.is_encrypted:
            raise InvalidResumeFileError(
                "Password-protected PDF files are not supported."
            )

        try:
            extracted_text = "\n".join(page.get_text() for page in document)
        except (pymupdf.FileDataError, RuntimeError, ValueError, OSError) as error:
            raise InvalidResumeFileError(
                "The uploaded PDF could not be read."
            ) from error

    if not extracted_text.strip():
        raise NoSelectableTextError(
            "No selectable text was found in this PDF. It may be scanned; OCR may be required."
        )

    return extracted_text


def extract_txt_text(txt_bytes: bytes) -> str:
    """Decode a UTF-8 TXT file, accepting and removing a UTF-8 byte-order mark.

    Raises:
        InvalidResumeFileError: If the file does not contain valid UTF-8 text.
    """
    if not _is_utf8_text(txt_bytes):
        raise InvalidResumeFileError("TXT files must use UTF-8 encoding.")

    try:
        return txt_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidResumeFileError("TXT files must use UTF-8 encoding.") from error
