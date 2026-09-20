"""
tests/test_integration.py — End-to-end integration tests.

Tests the full pipeline: parse report → summarize → export JSON/PDF.
Requires valid API credentials to run.
"""

import json
import pytest
from pathlib import Path

from report_parser import parse_report
from schema import HealthReportAnalysis
from exporter import generate_pdf_report, generate_json_export


# Sample synthetic report for pipeline testing
SAMPLE_REPORT = """
PATIENT DIAGNOSTIC LABORATORY REPORT
Patient Name: Integration Test | Age: 45 | Gender: Female | Date: 15-Mar-2025

COMPLETE BLOOD COUNT (CBC):
- Hemoglobin (Hb): 11.5 g/dL (Reference Range: 12.0 - 16.0) [LOW]
- White Blood Cells (WBC): 7.2 x10^3/uL (Reference Range: 4.5 - 11.0) [Normal]
- Platelets: 180 x10^3/uL (Reference Range: 150 - 450) [Normal]

LIPID PROFILE:
- Total Cholesterol: 230 mg/dL (Reference Range: < 200) [HIGH]
- HDL Cholesterol: 55 mg/dL (Reference Range: > 40) [Normal]
- LDL Cholesterol: 145 mg/dL (Reference Range: < 100) [HIGH]
"""


class TestParseAndExportPipeline:
    """Tests that don't require API calls — parse + export only."""

    def test_parse_text_report(self) -> None:
        """Test that text parsing succeeds for a valid report."""
        text = parse_report(SAMPLE_REPORT, file_type="text")
        assert "Hemoglobin" in text
        assert "Cholesterol" in text

    def test_export_pdf_from_analysis(self) -> None:
        """Test PDF generation from a manually constructed HealthReportAnalysis."""
        analysis = HealthReportAnalysis(
            is_valid_report=True,
            report_title="Integration Test Report",
            patient_summary="Test patient with elevated cholesterol and low hemoglobin.",
            biomarkers=[],
            key_findings=["Elevated LDL cholesterol", "Low hemoglobin"],
            questions_for_doctor=["Should I adjust my diet?"],
        )
        pdf_bytes = generate_pdf_report(analysis)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100
        # PDF files start with %PDF
        assert pdf_bytes[:5] == b"%PDF-"

    def test_export_json_from_analysis(self) -> None:
        """Test JSON export from a HealthReportAnalysis instance."""
        analysis = HealthReportAnalysis(
            is_valid_report=True,
            report_title="JSON Export Test",
            patient_summary="All values within normal range.",
        )
        json_str = generate_json_export(analysis)
        parsed = json.loads(json_str)
        assert parsed["is_valid_report"] is True
        assert parsed["report_title"] == "JSON Export Test"

    def test_export_json_roundtrip(self) -> None:
        """Test that JSON export can be parsed back into a model."""
        analysis = HealthReportAnalysis(
            is_valid_report=True,
            report_title="Roundtrip Test",
            patient_summary="Testing roundtrip serialization.",
            key_findings=["Finding 1", "Finding 2"],
        )
        json_str = generate_json_export(analysis)
        restored = HealthReportAnalysis.model_validate_json(json_str)
        assert restored.report_title == "Roundtrip Test"
        assert len(restored.key_findings) == 2


@pytest.mark.integration
class TestFullPipelineIntegration:
    """
    Full pipeline integration tests requiring valid API credentials.
    Run with: pytest tests/test_integration.py -m integration -v
    """

    def test_full_text_pipeline(self) -> None:
        """Test: parse text → summarize (Detailed) → export PDF + JSON."""
        try:
            from medical_summarizer import MedicalSummarizer

            summarizer = MedicalSummarizer()

            # Step 1: Summarize
            result = summarizer.summarize(
                SAMPLE_REPORT, summary_type="Detailed", file_type="text"
            )
            assert "summary" in result
            assert "raw_json" in result

            # Step 2: Validate JSON structure
            summary_data = result["summary"]
            assert isinstance(summary_data, dict)

            # Step 3: Attempt PDF export (only if we got a full HealthReportAnalysis)
            if "biomarkers" in summary_data:
                analysis = HealthReportAnalysis.model_validate(summary_data)
                pdf_bytes = generate_pdf_report(analysis)
                assert len(pdf_bytes) > 100

        except ValueError:
            pytest.skip("No AI provider configured")

    def test_full_pdf_pipeline(self) -> None:
        """Test: parse PDF → summarize → export (if sample PDF exists)."""
        sample_path = Path(__file__).parent.parent / "samples" / "sample_health_report.pdf"
        if not sample_path.exists():
            sample_path = Path(__file__).parent.parent / "sample_health_report.pdf"

        if not sample_path.exists():
            pytest.skip("No sample PDF file found")

        try:
            from medical_summarizer import MedicalSummarizer

            summarizer = MedicalSummarizer()
            pdf_bytes = sample_path.read_bytes()

            result = summarizer.summarize(pdf_bytes, summary_type="Detailed", file_type="pdf")
            assert "summary" in result

        except ValueError:
            pytest.skip("No AI provider configured")
