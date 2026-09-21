"""
report_parser.py — PDF & text parsing logic for medical report ingestion.

Supports:
- PDF text extraction via pdfplumber (primary) with pypdf fallback
- Plain text / string inputs
- File size validation (< 50 MB)
"""

import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class ReportParsingError(Exception):
    """Raised when a report cannot be parsed."""
    pass


def validate_file_size(data: bytes) -> None:
    """
    Validate that the file does not exceed the maximum allowed size.

    Args:
        data: Raw file bytes.

    Raises:
        ReportParsingError: If the file exceeds MAX_FILE_SIZE_BYTES.
    """
    if len(data) > MAX_FILE_SIZE_BYTES:
        size_mb = len(data) / (1024 * 1024)
        raise ReportParsingError(
            f"File size ({size_mb:.1f} MB) exceeds the maximum allowed size of "
            f"{MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB."
        )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text content from PDF bytes using pdfplumber (primary)
    with pypdf as a fallback.

    Args:
        pdf_bytes: Raw PDF file bytes.

    Returns:
        Extracted text content from the PDF.

    Raises:
        ReportParsingError: If text extraction fails entirely.
    """
    validate_file_size(pdf_bytes)

    # Primary: pdfplumber (more accurate for tabular lab reports)
    try:
        import pdfplumber

        text_pages: list[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)

        extracted = "\n".join(text_pages).strip()
        if len(extracted) > 30:
            logger.info(
                f"pdfplumber extracted {len(extracted)} chars from "
                f"{len(text_pages)} page(s)."
            )
            return extracted
    except ImportError:
        logger.warning("pdfplumber not installed; falling back to pypdf.")
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}; trying pypdf fallback.")

    # Fallback: pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_pages.append(page_text)

        extracted = "\n".join(text_pages).strip()
        if len(extracted) > 30:
            logger.info(
                f"pypdf extracted {len(extracted)} chars from "
                f"{len(text_pages)} page(s)."
            )
            return extracted
    except ImportError:
        logger.error("Neither pdfplumber nor pypdf is installed.")
    except Exception as e:
        logger.error(f"pypdf extraction also failed: {e}")

    # If both methods failed or returned very little text
    return ""


def parse_text_input(text: str) -> str:
    """
    Validate and clean raw text input for processing.

    Args:
        text: Raw text string from user input.

    Returns:
        Cleaned text string.

    Raises:
        ReportParsingError: If the text is empty or too short.
    """
    if not text or not text.strip():
        raise ReportParsingError("No text content provided. Please paste a medical report.")

    cleaned = text.strip()
    if len(cleaned) < 20:
        raise ReportParsingError(
            "Input text is too short to be a valid medical report. "
            "Please provide the full report text."
        )

    return cleaned


def parse_report(
    source: str | bytes,
    file_type: str = "text"
) -> str:
    """
    Unified entry point for parsing medical reports from various sources.

    Args:
        source: Either raw text (str) or file bytes (bytes).
        file_type: One of 'text', 'pdf'. Determines parsing strategy.

    Returns:
        Extracted text content ready for AI analysis.

    Raises:
        ReportParsingError: If parsing fails.
        ValueError: If file_type is unsupported.
    """
    if file_type not in ("text", "pdf"):
        raise ValueError(
            f"Unsupported file type: '{file_type}'. Supported types: 'text', 'pdf'."
        )

    if file_type == "text":
        text = source if isinstance(source, str) else source.decode("utf-8", errors="ignore")
        return parse_text_input(text)

    if file_type == "pdf" and isinstance(source, bytes):
        validate_file_size(source)
        extracted = extract_text_from_pdf(source)
        if not extracted:
            logger.warning("PDF text extraction returned empty; document may be image-based.")
            return ""
        return extracted

    if file_type == "pdf" and isinstance(source, str):
        return parse_text_input(source)

    raise ValueError(
        f"Unsupported file type: '{file_type}'. Supported types: 'text', 'pdf'."
    )
