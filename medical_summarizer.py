"""
medical_summarizer.py — Core summarization engine using Anthropic Claude API.

Provides structured medical report analysis with three summary modes:
- Brief: Quick 2-3 sentence overview with alerts
- Detailed: Full biomarker extraction, jargon translation, doctor questions, and lifestyle tips
- Highlighted: Abnormal-only focus with risk categorization

Falls back to Google Gemini if Anthropic is not configured.
"""

import json
import logging
import time
from typing import Any

from config import (
    get_anthropic_api_key,
    is_anthropic_configured,
    is_api_key_configured,
    CLAUDE_MODEL,
    MAX_TOKENS,
    TIMEOUT_SECONDS,
    ANALYSIS_SYSTEM_INSTRUCTION,
)
from report_parser import parse_report, ReportParsingError
from schema import (
    HealthReportAnalysis,
    BriefSummary,
    DetailedSummary,
    HighlightedSummary,
)

logger = logging.getLogger(__name__)

# Maximum retry attempts for transient API errors
MAX_RETRIES = 3

# ──────────────────────────────────────────────
# Summary Mode Prompts
# ──────────────────────────────────────────────

BRIEF_PROMPT = """
Analyze the following medical report and provide a BRIEF summary.
Return a JSON object with these fields:
- "report_title": A short descriptive title
- "overview": A 2-3 sentence executive overview of the findings
- "immediate_alerts": A list of strings for critical or abnormal findings
- "overall_status": One of "Normal", "Attention Needed", or "Urgent Review"

Be concise, accurate, and non-alarmist.
"""

DETAILED_PROMPT = """
Analyze the following medical report and provide a DETAILED structured analysis.
Return a JSON object with these fields:
- "is_valid_report": true if this is a valid medical report, false otherwise
- "unvalid_reason": reason string if not valid, else null
- "report_title": descriptive title of the report
- "patient_summary": 2-3 sentence executive overview
- "biomarkers": array of objects, each with:
    - "parameter_name": test name
    - "value": result value
    - "unit": measurement unit
    - "reference_range": normal range
    - "status": "Normal", "High", "Low", or "Critical"
    - "simple_explanation": 1-sentence plain English explanation
- "key_findings": array of key takeaway strings
- "medical_jargon_decoded": array of objects with "term" and "plain_english"
- "questions_for_doctor": 3-5 recommended questions
- "lifestyle_wellness_educational_tips": array of health tips

Be thorough, accurate, compassionate, and non-alarmist.
"""

HIGHLIGHTED_PROMPT = """
Analyze the following medical report and HIGHLIGHT ONLY the abnormal findings.
Return a JSON object with these fields:
- "report_title": title focused on abnormal findings
- "patient_summary": brief overview focused on what needs attention
- "abnormal_biomarkers": array of ONLY abnormal biomarkers (High, Low, Critical), each with:
    - "parameter_name": test name
    - "value": result value
    - "unit": measurement unit
    - "reference_range": normal range
    - "status": "High", "Low", or "Critical"
    - "simple_explanation": 1-sentence explanation of why this matters
- "risk_flags": array of risk alert strings categorized by severity
- "priority_actions": array of recommended follow-up actions
- "questions_for_doctor": targeted questions about the abnormal findings

Focus ONLY on abnormal results. Ignore normal values. Be actionable and non-alarmist.
"""

SUMMARY_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "Brief": {"prompt": BRIEF_PROMPT, "model_cls": BriefSummary},
    "Detailed": {"prompt": DETAILED_PROMPT, "model_cls": DetailedSummary},
    "Highlighted": {"prompt": HIGHLIGHTED_PROMPT, "model_cls": HighlightedSummary},
}


class MedicalSummarizer:
    """
    Core summarization engine that uses Anthropic Claude for medical report analysis.
    Falls back to Google Gemini when Claude credentials are not available.
    """

    def __init__(self) -> None:
        """Initialize the summarizer with the available AI provider."""
        self._provider: str = "none"
        self._claude_client: Any = None
        self._gemini_analyzer: Any = None
        self._gemini_client: Any = None

        # Prefer Gemini (free tier) — use Anthropic only if explicitly configured
        if is_api_key_configured():
            try:
                from gemini_engine import HealthReportAnalyzer
                from google import genai
                from config import get_api_key, MODEL_NAME

                self._gemini_analyzer = HealthReportAnalyzer()
                self._gemini_client = genai.Client(api_key=get_api_key())
                self._provider = "gemini"
                logger.info("MedicalSummarizer initialized with Google Gemini (free tier).")
            except Exception as e:
                logger.error(f"Gemini initialization failed: {e}")

        if self._provider == "none" and is_anthropic_configured():
            try:
                from anthropic import Anthropic

                self._claude_client = Anthropic(
                    api_key=get_anthropic_api_key(),
                    timeout=TIMEOUT_SECONDS,
                )
                self._provider = "anthropic"
                logger.info("MedicalSummarizer initialized with Anthropic Claude.")
            except ImportError:
                logger.warning("anthropic package not installed.")

        if self._provider == "none":
            raise ValueError(
                "No AI provider configured. Please set GEMINI_API_KEY in your .env file."
            )

    @property
    def provider(self) -> str:
        """Return the active AI provider name."""
        return self._provider

    def summarize(
        self,
        source: str | bytes,
        summary_type: str = "Detailed",
        file_type: str = "text",
    ) -> dict[str, Any]:
        """
        Process a medical report and return a structured summary.

        Args:
            source: Raw text string or file bytes.
            summary_type: One of 'Brief', 'Detailed', or 'Highlighted'.
            file_type: Input format — 'text' or 'pdf'.

        Returns:
            Dictionary with 'summary' (parsed model dict) and 'raw_json' (JSON string).

        Raises:
            ValueError: If summary_type is unsupported.
            ReportParsingError: If the input cannot be parsed.
            RuntimeError: If the AI API call fails after retries.
        """
        if summary_type not in SUMMARY_MODE_CONFIG:
            raise ValueError(
                f"Unsupported summary type: '{summary_type}'. "
                f"Choose from: {list(SUMMARY_MODE_CONFIG.keys())}"
            )

        # Parse the report text
        report_text = parse_report(source, file_type=file_type)

        if not report_text and file_type == "pdf" and isinstance(source, bytes):
            # Image-based PDF — pass raw bytes to Gemini (Claude doesn't support PDF bytes)
            if self._provider == "gemini" and self._gemini_analyzer is not None:
                result = self._gemini_analyzer.analyze_report(source, file_type="pdf")
                return {
                    "summary": result.model_dump(),
                    "raw_json": result.model_dump_json(indent=2),
                }
            else:
                raise ReportParsingError(
                    "PDF appears to be image-based (scanned). Text extraction failed. "
                    "Please try pasting the report text manually."
                )

        # Route to the appropriate provider
        if self._provider == "gemini":
            return self._summarize_with_gemini(report_text, source, file_type, summary_type)
        else:
            return self._summarize_with_claude(report_text, summary_type)

    def _summarize_with_claude(
        self, report_text: str, summary_type: str
    ) -> dict[str, Any]:
        """
        Send report text to Claude for structured summarization.

        Args:
            report_text: Extracted report text.
            summary_type: Summary mode key.

        Returns:
            Parsed summary dict and raw JSON string.
        """
        config = SUMMARY_MODE_CONFIG[summary_type]
        mode_prompt = config["prompt"]
        model_cls = config["model_cls"]

        user_message = f"{mode_prompt}\n\n--- MEDICAL REPORT ---\n{report_text}\n--- END REPORT ---"

        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = self._claude_client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=MAX_TOKENS,
                    system=ANALYSIS_SYSTEM_INSTRUCTION,
                    messages=[{"role": "user", "content": user_message}],
                )

                # Extract text content from response
                raw_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        raw_text += block.text

                # Clean markdown code fences if present
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                # Parse into Pydantic model
                parsed = model_cls.model_validate_json(cleaned)

                return {
                    "summary": parsed.model_dump(),
                    "raw_json": parsed.model_dump_json(indent=2),
                }

            except Exception as e:
                last_exception = e
                err_str = str(e)
                # Retry on transient errors (rate limit, overloaded, server error)
                if any(code in err_str for code in ["529", "503", "500", "rate_limit"]):
                    wait = 2 ** attempt
                    logger.warning(
                        f"Claude API transient error (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                    continue
                else:
                    logger.error(f"Claude API non-retryable error: {e}")
                    break

        raise RuntimeError(
            f"Claude API summarization failed after {MAX_RETRIES} attempts: "
            f"{str(last_exception)}"
        )

    def _summarize_with_gemini(
        self,
        report_text: str,
        source: str | bytes,
        file_type: str,
        summary_type: str = "Detailed",
    ) -> dict[str, Any]:
        """
        Summarization using Google Gemini (free tier).
        Supports Brief, Detailed, and Highlighted summary modes via text prompting.

        Args:
            report_text: Extracted report text.
            source: Original source data.
            file_type: Original file type.
            summary_type: One of 'Brief', 'Detailed', 'Highlighted'.

        Returns:
            Parsed summary dict and raw JSON string.
        """
        if self._gemini_client is None:
            raise RuntimeError("Gemini client is not initialized.")

        from google.genai import types as gtypes
        from config import MODEL_NAME, ANALYSIS_SYSTEM_INSTRUCTION

        config = SUMMARY_MODE_CONFIG[summary_type]
        mode_prompt = config["prompt"]
        model_cls = config["model_cls"]

        user_message = (
            f"{mode_prompt}\n\n--- MEDICAL REPORT ---\n{report_text}\n--- END REPORT ---"
        )

        last_exception: Exception | None = None
        models_to_try = [MODEL_NAME, "gemini-1.5-flash", "gemini-1.5-flash-8b"]

        for model in models_to_try:
            for attempt in range(3):
                try:
                    response = self._gemini_client.models.generate_content(
                        model=model,
                        contents=user_message,
                        config=gtypes.GenerateContentConfig(
                            system_instruction=ANALYSIS_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )

                    raw_text = response.text or ""
                    cleaned = raw_text.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()

                    parsed = model_cls.model_validate_json(cleaned)
                    return {
                        "summary": parsed.model_dump(),
                        "raw_json": parsed.model_dump_json(indent=2),
                    }

                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                        import time
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        break

        # Final fallback: use the structured gemini_engine analyzer (Detailed mode)
        if self._gemini_analyzer is not None:
            logger.warning("Text-mode Gemini summarization failed; falling back to structured analyzer.")
            result = self._gemini_analyzer.analyze_report(
                report_text if file_type == "text" else source,
                file_type=file_type,
            )
            return {
                "summary": result.model_dump(),
                "raw_json": result.model_dump_json(indent=2),
            }

        raise RuntimeError(
            f"Gemini summarization failed across all models: {str(last_exception)}"
        )

    def process(
        self,
        file_obj: Any,
        summary_type: str = "Detailed",
    ) -> dict[str, Any]:
        """
        Gradio-compatible entry point. Accepts a Gradio file object or text.

        Args:
            file_obj: A file path string (from gr.File) or raw text string.
            summary_type: Summary mode.

        Returns:
            Dictionary with 'summary' and 'raw_json'.
        """
        if file_obj is None:
            raise ValueError("No file or text provided.")

        # Gradio gr.File returns a file path string
        if isinstance(file_obj, str):
            from pathlib import Path

            path = Path(file_obj)
            if path.is_file():
                suffix = path.suffix.lower()
                if suffix == ".pdf":
                    data = path.read_bytes()
                    return self.summarize(data, summary_type=summary_type, file_type="pdf")
                elif suffix in (".txt", ".text"):
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    return self.summarize(text, summary_type=summary_type, file_type="text")
                else:
                    # Try reading as text
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    return self.summarize(text, summary_type=summary_type, file_type="text")
            else:
                # Raw text string pasted by user
                return self.summarize(file_obj, summary_type=summary_type, file_type="text")

        raise ValueError(f"Unsupported input type: {type(file_obj)}")
