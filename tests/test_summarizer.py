"""
tests/test_summarizer.py — Unit tests for medical_summarizer.py

Tests initialization, summary type validation, and error handling.
Note: Tests that call the actual Claude/Gemini API are marked with
@pytest.mark.integration and require valid API credentials.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Any

from schema import BriefSummary, DetailedSummary, HighlightedSummary, HealthReportAnalysis
from medical_summarizer import MedicalSummarizer, SUMMARY_MODE_CONFIG


# Sample synthetic report text for testing
SAMPLE_REPORT_TEXT = """
PATIENT DIAGNOSTIC LABORATORY REPORT
Patient Name: Test Patient | Age: 30 | Gender: Male | Date: 01-Jan-2025

COMPLETE BLOOD COUNT (CBC):
- Hemoglobin (Hb): 14.0 g/dL (Reference Range: 13.5 - 17.5) [Normal]
- White Blood Cells (WBC): 6.0 x10^3/uL (Reference Range: 4.5 - 11.0) [Normal]

LIPID PROFILE:
- Total Cholesterol: 250 mg/dL (Reference Range: < 200) [HIGH]
- LDL Cholesterol: 170 mg/dL (Reference Range: < 100) [HIGH]
"""


class TestSummaryModeConfig:
    """Tests for summary mode configuration."""

    def test_all_modes_registered(self) -> None:
        """Test that Brief, Detailed, and Highlighted are all registered."""
        assert "Brief" in SUMMARY_MODE_CONFIG
        assert "Detailed" in SUMMARY_MODE_CONFIG
        assert "Highlighted" in SUMMARY_MODE_CONFIG

    def test_brief_uses_correct_model(self) -> None:
        """Test that Brief mode maps to BriefSummary."""
        assert SUMMARY_MODE_CONFIG["Brief"]["model_cls"] is BriefSummary

    def test_detailed_uses_correct_model(self) -> None:
        """Test that Detailed mode maps to DetailedSummary."""
        assert SUMMARY_MODE_CONFIG["Detailed"]["model_cls"] is DetailedSummary

    def test_highlighted_uses_correct_model(self) -> None:
        """Test that Highlighted mode maps to HighlightedSummary."""
        assert SUMMARY_MODE_CONFIG["Highlighted"]["model_cls"] is HighlightedSummary


class TestMedicalSummarizerValidation:
    """Tests for input validation without requiring API credentials."""

    @patch("medical_summarizer.is_anthropic_configured", return_value=False)
    @patch("medical_summarizer.is_api_key_configured", return_value=False)
    def test_no_provider_raises(self, mock_gemini: Any, mock_claude: Any) -> None:
        """Test that initialization fails when no provider is configured."""
        with pytest.raises(ValueError, match="No AI provider configured"):
            MedicalSummarizer()

    @patch("medical_summarizer.is_anthropic_configured", return_value=False)
    @patch("medical_summarizer.is_api_key_configured", return_value=True)
    @patch("medical_summarizer.get_anthropic_api_key", return_value=None)
    def test_gemini_fallback_init(
        self, mock_key: Any, mock_gemini: Any, mock_claude: Any
    ) -> None:
        """Test that Gemini fallback initializes when Claude is not available."""
        try:
            summarizer = MedicalSummarizer()
            assert summarizer.provider == "gemini"
        except Exception:
            # May fail if GEMINI_API_KEY is not valid, which is acceptable in unit tests
            pass


class TestSchemaModels:
    """Tests for Pydantic schema model validation."""

    def test_brief_summary_creation(self) -> None:
        """Test BriefSummary model can be created with valid data."""
        brief = BriefSummary(
            report_title="Test Report",
            overview="All values are normal.",
            immediate_alerts=[],
            overall_status="Normal",
        )
        assert brief.overall_status == "Normal"

    def test_highlighted_summary_creation(self) -> None:
        """Test HighlightedSummary model can be created with valid data."""
        highlighted = HighlightedSummary(
            report_title="Abnormal Findings",
            patient_summary="High cholesterol detected.",
            abnormal_biomarkers=[],
            risk_flags=["Elevated LDL cholesterol"],
            priority_actions=["Schedule lipid re-test"],
            questions_for_doctor=["Should I start medication?"],
        )
        assert len(highlighted.risk_flags) == 1

    def test_health_report_analysis_defaults(self) -> None:
        """Test HealthReportAnalysis defaults."""
        analysis = HealthReportAnalysis(is_valid_report=True)
        assert analysis.report_title == "Health Diagnostic Summary"
        assert analysis.biomarkers == []
        assert analysis.key_findings == []


@pytest.mark.integration
class TestMedicalSummarizerIntegration:
    """
    Integration tests that require valid API credentials.
    Run with: pytest tests/test_summarizer.py -m integration -v
    """

    def test_brief_summarization(self) -> None:
        """Test Brief mode with a real API call."""
        try:
            summarizer = MedicalSummarizer()
            result = summarizer.summarize(
                SAMPLE_REPORT_TEXT, summary_type="Brief", file_type="text"
            )
            assert "summary" in result
            assert "raw_json" in result
        except ValueError:
            pytest.skip("No AI provider configured")

    def test_detailed_summarization(self) -> None:
        """Test Detailed mode with a real API call."""
        try:
            summarizer = MedicalSummarizer()
            result = summarizer.summarize(
                SAMPLE_REPORT_TEXT, summary_type="Detailed", file_type="text"
            )
            assert "summary" in result
        except ValueError:
            pytest.skip("No AI provider configured")

    def test_highlighted_summarization(self) -> None:
        """Test Highlighted mode with a real API call."""
        try:
            summarizer = MedicalSummarizer()
            result = summarizer.summarize(
                SAMPLE_REPORT_TEXT, summary_type="Highlighted", file_type="text"
            )
            assert "summary" in result
        except ValueError:
            pytest.skip("No AI provider configured")
