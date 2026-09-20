"""
schema.py — Pydantic models for medical report data validation.

Defines the structured output schema for AI analysis including
biomarkers, medical term translations, and summary modes
(Brief, Detailed, Highlighted).
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field, model_validator, field_validator


class Biomarker(BaseModel):
    """A single lab test parameter or biomarker extracted from a report."""

    parameter_name: str = Field(
        description="Name of the lab test or biomarker (e.g., Total Cholesterol, Hemoglobin)"
    )
    value: str = Field(
        description="Observed value from the test result"
    )
    unit: str = Field(
        description="Unit of measurement (e.g., mg/dL, g/dL, mIU/L, or N/A)"
    )
    reference_range: str = Field(
        description="Standard normal reference range provided by the lab"
    )
    status: str = Field(
        description="Status classification: 'Normal', 'High', 'Low', or 'Critical'"
    )
    simple_explanation: str = Field(
        description="Brief 1-sentence explanation of what this biomarker measures"
    )

    @field_validator("parameter_name", "value", "unit", "reference_range", "status", "simple_explanation", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class MedicalTermTranslation(BaseModel):
    """A medical jargon term decoded into plain English."""

    term: str = Field(
        description="Medical jargon term (e.g., Hyperlipidemia, TSH)"
    )
    plain_english: str = Field(
        description="Plain English definition and what it means for the patient"
    )

    @field_validator("term", "plain_english", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class HealthReportAnalysis(BaseModel):
    """
    Complete structured analysis output from a medical report.
    Used as the response schema for both Gemini and Claude engines.
    """

    is_valid_report: bool = Field(
        description="True if the input is a valid health or medical diagnostic report, False otherwise"
    )
    unvalid_reason: Optional[str] = Field(
        default=None,
        description="Reason if the file is not a valid medical report"
    )
    report_title: str = Field(
        default="Health Diagnostic Summary",
        description="Descriptive title of the report (e.g., Lipid & CBC Panel Summary)"
    )
    patient_name: Optional[str] = Field(
        default=None,
        description="Patient name if mentioned in the report"
    )
    patient_age: Optional[str] = Field(
        default=None,
        description="Patient age if mentioned in the report"
    )
    patient_gender: Optional[str] = Field(
        default=None,
        description="Patient gender if mentioned in the report"
    )
    test_date: Optional[str] = Field(
        default=None,
        description="Date of the report or sample collection if mentioned"
    )
    patient_summary: str = Field(
        default="",
        description="Executive 2-3 sentence overview of the health report results"
    )
    biomarkers: list[Biomarker] = Field(
        default_factory=list,
        description="List of all extracted biomarkers and test parameters"
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key takeaways, highlights, or abnormal finding alerts"
    )
    medical_jargon_decoded: list[MedicalTermTranslation] = Field(
        default_factory=list,
        description="List of technical terms decoded into simple English"
    )
    medications_or_treatment: list[str] = Field(
        default_factory=list,
        description="Medications, clinical treatments, or drug considerations mentioned or suggested"
    )
    questions_for_doctor: list[str] = Field(
        default_factory=list,
        description="3-5 recommended questions to ask during doctor consultation"
    )
    lifestyle_wellness_educational_tips: list[str] = Field(
        default_factory=list,
        description="General educational health tips and recommendations related to the report findings"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Alias for lifestyle_wellness_educational_tips — LLMs may return this key directly"
    )

    @field_validator("patient_name", "patient_age", "patient_gender", "test_date", "report_title", "patient_summary", mode="before")
    @classmethod
    def coerce_opt_string(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @model_validator(mode="after")
    def merge_recommendations(self) -> "HealthReportAnalysis":
        """If LLM returned 'recommendations', merge into lifestyle_wellness_educational_tips."""
        if self.recommendations and not self.lifestyle_wellness_educational_tips:
            self.lifestyle_wellness_educational_tips = self.recommendations
        elif self.lifestyle_wellness_educational_tips and not self.recommendations:
            self.recommendations = self.lifestyle_wellness_educational_tips
        return self


# ──────────────────────────────────────────────
# Summary Mode Schemas
# ──────────────────────────────────────────────

class BriefSummary(BaseModel):
    """Quick 2-3 sentence overview with immediate alerts."""

    report_title: str = Field(
        default="Health Report Brief",
        description="Short title for the report"
    )
    overview: str = Field(
        description="2-3 sentence executive overview of the report findings"
    )
    immediate_alerts: list[str] = Field(
        default_factory=list,
        description="List of critical or abnormal findings requiring immediate attention"
    )
    overall_status: str = Field(
        default="Review Recommended",
        description="Overall health status: 'Normal', 'Attention Needed', or 'Urgent Review'"
    )


class DetailedSummary(HealthReportAnalysis):
    """
    Full detailed analysis — extends the base HealthReportAnalysis
    with all biomarkers, clinical context, doctor questions, and lifestyle advice.
    This is effectively the same as HealthReportAnalysis.
    """
    pass


class HighlightedSummary(BaseModel):
    """Abnormal-only focus with risk flags for high/low/critical values."""

    report_title: str = Field(
        default="Abnormal Findings Highlight",
        description="Title for the highlighted summary"
    )
    patient_summary: str = Field(
        default="",
        description="Brief overview focused on abnormal findings"
    )
    abnormal_biomarkers: list[Biomarker] = Field(
        default_factory=list,
        description="Only biomarkers that are High, Low, or Critical"
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Risk flag alerts categorized by severity"
    )
    priority_actions: list[str] = Field(
        default_factory=list,
        description="Priority follow-up actions recommended for abnormal findings"
    )
    questions_for_doctor: list[str] = Field(
        default_factory=list,
        description="Targeted questions about the abnormal findings"
    )
