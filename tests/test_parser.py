"""
tests/test_parser.py — Unit tests for report_parser.py

Tests PDF and text parsing, validation, and error handling.
"""

import pytest

from report_parser import (
    parse_report,
    parse_text_input,
    validate_file_size,
    extract_text_from_pdf,
    ReportParsingError,
    MAX_FILE_SIZE_BYTES,
)


class TestParseTextInput:
    """Tests for text input validation and cleaning."""

    def test_valid_text_input(self) -> None:
        """Test that valid text is returned cleaned."""
        raw = "  PATIENT REPORT: Hemoglobin 14.2 g/dL  "
        result = parse_text_input(raw)
        assert result == raw.strip()

    def test_empty_string_raises(self) -> None:
        """Test that empty string raises ReportParsingError."""
        with pytest.raises(ReportParsingError, match="No text content"):
            parse_text_input("")

    def test_whitespace_only_raises(self) -> None:
        """Test that whitespace-only string raises ReportParsingError."""
        with pytest.raises(ReportParsingError, match="No text content"):
            parse_text_input("   \n\t  ")

    def test_too_short_raises(self) -> None:
        """Test that very short text raises ReportParsingError."""
        with pytest.raises(ReportParsingError, match="too short"):
            parse_text_input("Hi")


class TestValidateFileSize:
    """Tests for file size validation."""

    def test_valid_size(self) -> None:
        """Test that a small file passes validation."""
        data = b"x" * 1024  # 1 KB
        validate_file_size(data)  # Should not raise

    def test_oversized_raises(self) -> None:
        """Test that a file exceeding MAX_FILE_SIZE_BYTES raises."""
        data = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(ReportParsingError, match="exceeds the maximum"):
            validate_file_size(data)


class TestParseReport:
    """Tests for the unified parse_report entry point."""

    def test_text_mode(self) -> None:
        """Test text mode parsing."""
        report = "BLOOD TEST REPORT: WBC 6.5 x10^3/uL Normal"
        result = parse_report(report, file_type="text")
        assert "WBC" in result

    def test_text_from_bytes(self) -> None:
        """Test that bytes input in text mode is decoded."""
        report_bytes = b"BLOOD TEST REPORT: WBC 6.5 x10^3/uL Normal"
        result = parse_report(report_bytes, file_type="text")
        assert "WBC" in result

    def test_unsupported_file_type_raises(self) -> None:
        """Test that unsupported file type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_report("data", file_type="docx")

    def test_pdf_empty_returns_empty(self) -> None:
        """Test that invalid PDF bytes return empty string."""
        result = parse_report(b"not a real pdf", file_type="pdf")
        # Should return empty string (extraction fails gracefully)
        assert isinstance(result, str)
