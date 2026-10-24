"""In-memory extraction of text PDFs; no OCR, execution, or upload retention."""

from io import BytesIO

from pypdf import PdfReader

from gapmap.apps.api.services.interfaces import PublicServiceError


MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_RESUME_CHARACTERS = 50_000
MAX_PAGE_CONTENT_BYTES = 5 * 1024 * 1024


class PDFInputError(PublicServiceError):
    def __init__(self, public_message: str, *, status_code: int = 422) -> None:
        super().__init__(public_message)
        self.status_code = status_code


def extract_pdf_text(data: bytes) -> str:
    if len(data) > MAX_PDF_BYTES:
        raise PDFInputError("Resume PDF exceeds the 5 MB limit. Use a smaller file or paste the resume text.", status_code=413)
    if not data.startswith(b"%PDF-"):
        raise PDFInputError("The upload is not a readable PDF. Upload a text-based PDF or paste the resume text.")
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise PDFInputError("Password-protected PDFs are not supported. Upload an unlocked PDF or paste the resume text.")
        if not 1 <= len(reader.pages) <= MAX_PDF_PAGES:
            raise PDFInputError("Resume PDFs must contain 1-20 pages. Upload a shorter PDF or paste the resume text.")
        parts = []
        total = 0
        for page in reader.pages:
            contents = page.get_contents()
            if contents is not None and len(contents.get_data()) > MAX_PAGE_CONTENT_BYTES:
                raise PDFInputError("The PDF is too complex to extract. Upload a simpler PDF or paste the resume text.")
            text = page.extract_text() or ""
            total += len(text) + (1 if parts else 0)
            if total > MAX_RESUME_CHARACTERS:
                raise PDFInputError("Extracted resume exceeds 50,000 characters. Shorten the resume or paste a shorter version.")
            parts.append(text)
        result = "\n".join(parts).strip()
        readable = sum(character.isalnum() for character in result)
        if readable < 20 or "\ufffd" in result:
            raise PDFInputError(
                "No readable resume text was found. The PDF may be scanned or image-only; "
                "OCR is not supported. Paste the resume text instead."
            )
        return result
    except PDFInputError:
        raise
    except Exception:
        # Malformed PDF internals may contain personal data; never return them.
        raise PDFInputError("The PDF could not be read. Upload a text-based PDF or paste the resume text instead.") from None
