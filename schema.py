from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class Biomarker(BaseModel):
    parameter_name: str = Field(description="Name of the lab test or biomarker (e.g., Total Cholesterol, Hemoglobin)")
    value: str = Field(description="Observed value from the test result")
    unit: str = Field(description="Unit of measurement (e.g., mg/dL, g/dL, mIU/L, or N/A)")
    reference_range: str = Field(description="Standard normal reference range provided by the lab")
    status: str = Field(description="Status classification: 'Normal', 'High', 'Low', or 'Critical'")
    simple_explanation: str = Field(description="Brief 1-sentence explanation of what this biomarker measures")

class MedicalTermTranslation(BaseModel):
    term: str = Field(description="Medical jargon term (e.g., Hyperlipidemia, TSH)")
    plain_english: str = Field(description="Plain English definition and what it means for the patient")

class HealthReportAnalysis(BaseModel):
    is_valid_report: bool = Field(description="True if the input is a valid health or medical diagnostic report, False otherwise")
    unvalid_reason: Optional[str] = Field(default=None, description="Reason if the file is not a valid medical report")
    report_title: str = Field(default="Health Diagnostic Summary", description="Descriptive title of the report (e.g., Lipid & CBC Panel Summary)")
    patient_summary: str = Field(default="", description="Executive 2-3 sentence overview of the health report results")
    biomarkers: List[Biomarker] = Field(default_factory=list, description="List of all extracted biomarkers and test parameters")
    key_findings: List[str] = Field(default_factory=list, description="Key takeaways, highlights, or abnormal finding alerts")
    medical_jargon_decoded: List[MedicalTermTranslation] = Field(default_factory=list, description="List of technical terms decoded into simple English")
    questions_for_doctor: List[str] = Field(default_factory=list, description="3-5 recommended questions to ask during doctor consultation")
    lifestyle_wellness_educational_tips: List[str] = Field(default_factory=list, description="General educational health tips related to the report findings")
