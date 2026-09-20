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
    MAX_TOKENS,
    ANALYSIS_SYSTEM_INSTRUCTION,
)
from schema import BriefSummary, DetailedSummary, HighlightedSummary

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Summary Mode Prompts
# ──────────────────────────────────────────────

BRIEF_PROMPT = """
Analyze the following medical report and provide a BRIEF summary.
Return a valid JSON object with EXACTLY these fields (no extra text, no markdown):
{
  "report_title": "short descriptive title",
  "overview": "2-3 sentence executive overview of findings",
  "immediate_alerts": ["list", "of", "critical findings"],
  "overall_status": "Normal" or "Attention Needed" or "Urgent Review"
}
"""

DETAILED_PROMPT = """
Analyze the following medical report and provide a DETAILED structured analysis.
Return a valid JSON object with EXACTLY these fields (no extra text, no markdown):
{
  "is_valid_report": true,
  "unvalid_reason": null,
  "report_title": "descriptive title",
  "patient_summary": "2-3 sentence executive overview",
  "biomarkers": [
    {
      "parameter_name": "test name",
      "value": "result value",
      "unit": "unit",
      "reference_range": "normal range",
      "status": "Normal or High or Low or Critical",
      "simple_explanation": "1-sentence plain English explanation"
    }
  ],
  "key_findings": ["finding 1", "finding 2"],
  "medical_jargon_decoded": [{"term": "medical term", "plain_english": "explanation"}],
  "questions_for_doctor": ["question 1", "question 2", "question 3"],
  "lifestyle_wellness_educational_tips": ["tip 1", "tip 2"]
}
"""

HIGHLIGHTED_PROMPT = """
Analyze the following medical report and highlight ONLY the abnormal findings.
Return a valid JSON object with EXACTLY these fields (no extra text, no markdown):
{
  "report_title": "title focused on abnormal findings",
  "patient_summary": "brief overview focused on what needs attention",
  "abnormal_biomarkers": [
    {
      "parameter_name": "test name",
      "value": "result value",
      "unit": "unit",
      "reference_range": "normal range",
      "status": "High or Low or Critical",
      "simple_explanation": "why this matters"
    }
  ],
  "risk_flags": ["risk alert 1", "risk alert 2"],
  "priority_actions": ["action 1", "action 2"],
  "questions_for_doctor": ["question 1", "question 2"]
}
"""

SUMMARY_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "Brief":       {"prompt": BRIEF_PROMPT,       "model_cls": BriefSummary},
    "Detailed":    {"prompt": DETAILED_PROMPT,     "model_cls": DetailedSummary},
    "Highlighted": {"prompt": HIGHLIGHTED_PROMPT,  "model_cls": HighlightedSummary},
}

# Fallback models if primary is unavailable
GROQ_MODEL_FALLBACKS = [GROQ_MODEL, "llama3-8b-8192", "mixtral-8x7b-32768"]


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

        user_message = (
            f"{mode_prompt}\n\n--- MEDICAL REPORT ---\n{report_text}\n--- END REPORT ---"
        )

        last_exception: Exception | None = None

        for model in GROQ_MODEL_FALLBACKS:
            for attempt in range(3):
                try:
                    response = self._client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": ANALYSIS_SYSTEM_INSTRUCTION},
                            {"role": "user",   "content": user_message},
                        ],
                        max_tokens=MAX_TOKENS,
                        temperature=0.1,
                        response_format={"type": "json_object"},
                    )

                    raw_text = response.choices[0].message.content or ""
                    cleaned = raw_text.strip()

                    # Strip markdown fences if present
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()

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
                        logger.error("Groq non-retryable error with model %s: %s", model, e)
                        break  # Try next model

        raise RuntimeError(
            f"Groq summarization failed across all models: {str(last_exception)}"
        )
