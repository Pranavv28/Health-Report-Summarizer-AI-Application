"""
groq_engine.py — AI summarization engine using Groq (free tier).

Uses the Groq Python SDK to call llama-3.3-70b-versatile for structured
medical report analysis. Supports Brief, Detailed, and Highlighted modes.
"""

import json
import logging
import time
from typing import Any

from groq import Groq

from config import (
    get_groq_api_key,
    GROQ_MODEL,
    GROQ_MODEL_FALLBACKS,
    MAX_TOKENS,
    ANALYSIS_SYSTEM_INSTRUCTION,
)
from schema import BriefSummary, DetailedSummary, HighlightedSummary

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Summary Mode Prompts
# ──────────────────────────────────────────────

BRIEF_PROMPT = """
Analyze the medical report and give a BRIEF summary. Be concise — 2-3 sentences max for overview.
Return ONLY a JSON object (no markdown, no extra text):
{
  "report_title": "short title (max 8 words)",
  "overview": "2-3 sentence overview only",
  "immediate_alerts": ["only critical findings, max 4 items"],
  "overall_status": "Normal" or "Attention Needed" or "Urgent Review"
}
"""

DETAILED_PROMPT = """
Analyze the medical report. Be concise and structured.
Return ONLY a JSON object (no markdown, no extra text):
{
  "is_valid_report": true,
  "unvalid_reason": null,
  "report_title": "short descriptive title (max 8 words)",
  "patient_name": "patient name if found in text, else null",
  "patient_age": "patient age if found, else null",
  "patient_gender": "patient gender if found, else null",
  "test_date": "report date if found, else null",
  "patient_summary": "2-3 sentence summary only",
  "biomarkers": [
    {"parameter_name": "name", "value": "result", "unit": "unit", "reference_range": "range", "status": "Normal|High|Low|Critical", "simple_explanation": "one short sentence"}
  ],
  "key_findings": ["max 5 key findings"],
  "medical_jargon_decoded": [{"term": "term", "plain_english": "brief plain explanation"}],
  "medications_or_treatment": ["relevant medications, clinical treatments, or drug considerations"],
  "questions_for_doctor": ["max 4 questions"],
  "lifestyle_wellness_educational_tips": ["max 4 lifestyle tips"],
  "recommendations": ["max 4 clinical recommendations based on abnormal findings"]
}
"""

HIGHLIGHTED_PROMPT = """
Analyze the medical report. List ONLY abnormal (High/Low/Critical) findings — skip all normal values.
Return ONLY a JSON object (no markdown, no extra text):
{
  "report_title": "short title focused on abnormal findings",
  "patient_summary": "1-2 sentences on what needs attention",
  "abnormal_biomarkers": [
    {"parameter_name": "name", "value": "result", "unit": "unit", "reference_range": "range", "status": "High|Low|Critical", "simple_explanation": "why this matters briefly"}
  ],
  "risk_flags": ["max 4 risk alerts"],
  "priority_actions": ["max 3 actions"],
  "questions_for_doctor": ["max 3 targeted questions"]
}
"""

SUMMARY_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "Brief":       {"prompt": BRIEF_PROMPT,       "model_cls": BriefSummary},
    "Detailed":    {"prompt": DETAILED_PROMPT,     "model_cls": DetailedSummary},
    "Highlighted": {"prompt": HIGHLIGHTED_PROMPT,  "model_cls": HighlightedSummary},
}

# GROQ_MODEL_FALLBACKS imported from config


class GroqSummarizer:
    """Medical report summarizer using Groq free-tier API."""

    def __init__(self) -> None:
        api_key = get_groq_api_key()
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in your .env file.")
        self._client = Groq(api_key=api_key)
        logger.info("GroqSummarizer initialized with model: %s", GROQ_MODEL)

    def summarize(self, report_text: str, summary_type: str = "Detailed") -> dict[str, Any]:
        """
        Summarize a medical report text using Groq.

        Args:
            report_text: Extracted plain-text medical report.
            summary_type: One of 'Brief', 'Detailed', 'Highlighted'.

        Returns:
            Dict with 'summary' (model dict) and 'raw_json' (JSON string).
        """
        if summary_type not in SUMMARY_MODE_CONFIG:
            raise ValueError(
                f"Unsupported summary type: '{summary_type}'. "
                f"Choose from: {list(SUMMARY_MODE_CONFIG.keys())}"
            )

        config = SUMMARY_MODE_CONFIG[summary_type]
        mode_prompt = config["prompt"]
        model_cls = config["model_cls"]

        # Truncate text if too long to avoid HTTP 413 (Entity Too Large)
        MAX_INPUT_CHARS = 12000
        if len(report_text) > MAX_INPUT_CHARS:
            report_text = report_text[:MAX_INPUT_CHARS] + "\n... [Report text truncated for LLM limits]"

        user_message = (
            f"{mode_prompt}\n\n--- MEDICAL REPORT ---\n{report_text}\n--- END REPORT ---"
        )

        last_exception: Exception | None = None

        for model in GROQ_MODEL_FALLBACKS:
            for attempt in range(3):
                try:
                    kwargs = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": ANALYSIS_SYSTEM_INSTRUCTION},
                            {"role": "user",   "content": user_message},
                        ],
                        "max_tokens": MAX_TOKENS,
                        "temperature": 0.1,
                    }
                    try:
                        response = self._client.chat.completions.create(
                            **kwargs, response_format={"type": "json_object"}
                        )
                    except Exception:
                        response = self._client.chat.completions.create(**kwargs)

                    raw_text = response.choices[0].message.content or ""
                    cleaned = raw_text.strip()

                    # Extract JSON object between first '{' and last '}'
                    start_idx = cleaned.find("{")
                    end_idx = cleaned.rfind("}")
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        cleaned = cleaned[start_idx : end_idx + 1]

                    parsed = model_cls.model_validate_json(cleaned)
                    logger.info("Groq summarization successful with model: %s", model)
                    return {
                        "summary": parsed.model_dump(),
                        "raw_json": parsed.model_dump_json(indent=2),
                    }

                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    # Retry on rate limit or server overload
                    if "429" in err_str or "503" in err_str or "rate_limit" in err_str.lower():
                        wait = 2 ** attempt
                        logger.warning("Groq rate limit (attempt %d), retrying in %ds...", attempt + 1, wait)
                        time.sleep(wait)
                        continue
                    else:
                        logger.error("Groq error with model %s: %s", model, e)
                        break  # Try next model

        raise RuntimeError(
            f"Groq summarization failed across all models: {str(last_exception)}"
        )
