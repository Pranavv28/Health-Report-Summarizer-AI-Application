import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Gemini Model Settings
MODEL_NAME = "gemini-3.6-flash"

def get_api_key() -> str | None:
    """Retrieve GEMINI_API_KEY from environment variables."""
    key = os.getenv("GEMINI_API_KEY")
    if key:
        key = key.strip()
    return key if key else None

def is_api_key_configured() -> bool:
    """Check if API key is present and non-empty."""
    key = get_api_key()
    return bool(key and len(key) > 5)

# Built-in Sample Reports for 1-click testing
SAMPLE_REPORTS = {
    "CBC & Lipid Panel (Blood Test)": """
PATIENT DIAGNOSTIC LABORATORY REPORT
Patient Name: John Doe | Age: 42 | Gender: Male | Date: 12-Oct-2025

COMPLETE BLOOD COUNT (CBC):
- White Blood Cells (WBC): 6.5 x10^3/uL (Reference Range: 4.5 - 11.0) [Normal]
- Red Blood Cells (RBC): 4.8 x10^6/uL (Reference Range: 4.3 - 5.9) [Normal]
- Hemoglobin (Hb): 14.2 g/dL (Reference Range: 13.5 - 17.5) [Normal]
- Hematocrit: 42.1 % (Reference Range: 41.0 - 50.0) [Normal]
- Platelets: 240 x10^3/uL (Reference Range: 150 - 450) [Normal]

LIPID PROFILE:
- Total Cholesterol: 245 mg/dL (Reference Range: < 200) [HIGH]
- Triglycerides: 210 mg/dL (Reference Range: < 150) [HIGH]
- HDL Cholesterol (Good): 38 mg/dL (Reference Range: > 40) [LOW]
- LDL Cholesterol (Bad): 165 mg/dL (Reference Range: < 100) [HIGH]
- Fasting Blood Glucose: 118 mg/dL (Reference Range: 70 - 99) [HIGH - Pre-diabetic Range]
    """,
    "Thyroid & Metabolic Panel": """
METABOLIC & THYROID HEALTH REPORT
Patient Name: Jane Smith | Age: 36 | Gender: Female | Date: 05-Nov-2025

THYROID PANEL:
- TSH (Thyroid Stimulating Hormone): 5.8 mIU/L (Reference Range: 0.4 - 4.0) [HIGH]
- Free T4 (Thyroxine): 0.7 ng/dL (Reference Range: 0.8 - 1.8) [LOW]
- Free T3 (Triiodothyronine): 2.1 pg/mL (Reference Range: 2.3 - 4.2) [LOW]

COMPREHENSIVE METABOLIC PANEL:
- Serum Sodium: 139 mEq/L (Reference Range: 135 - 145) [Normal]
- Serum Potassium: 4.2 mEq/L (Reference Range: 3.5 - 5.0) [Normal]
- Serum Creatinine: 0.9 mg/dL (Reference Range: 0.6 - 1.1) [Normal]
- Blood Urea Nitrogen (BUN): 16 mg/dL (Reference Range: 7 - 20) [Normal]
- ALT (Liver Enzyme): 22 U/L (Reference Range: 7 - 56) [Normal]
- AST (Liver Enzyme): 19 U/L (Reference Range: 10 - 40) [Normal]
    """
}

ANALYSIS_SYSTEM_INSTRUCTION = """
You are a highly meticulous, compassionate medical report analysis AI assistant.
Your goal is to parse medical diagnostic reports (blood tests, lab panels, radiology notes, clinical summaries) and provide structured, accurate, and easy-to-understand insights.

Instructions:
1. Validate whether the provided document or text is a genuine medical diagnostic report or lab test.
2. If it is NOT a medical report, set `is_valid_report` to false and provide a polite `unvalid_reason`.
3. Extract all biomarkers and test parameters accurately (Name, Result Value, Unit, Reference Range, and Status).
4. Assign status to each parameter: "Normal", "High", "Low", or "Critical".
5. Translate complex medical terms into plain, everyday English.
6. Generate 3 to 5 clear, targeted questions the patient should ask their doctor during their next visit.
7. Always maintain an encouraging, non-alarmist tone.
8. Educational purpose disclaimer: Remind the user that AI analysis is educational and does not replace direct medical advice from a physician.
"""
