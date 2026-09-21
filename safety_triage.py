"""Deterministic safeguards for critical values explicitly present in a report."""

import re
from typing import Any

EMERGENCY_DISCLAIMER = (
    "If you have chest pain, difficulty breathing, severe bleeding, fainting, seizures, "
    "confusion, or feel seriously unwell, seek emergency care immediately."
)

CRITICAL_URGENCY = "Critical/Emergency"


def _numeric_value(value: Any) -> float | None:
    """Extract the first numeric value without inferring units or a diagnosis."""
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def _critical_flag(parameter_name: str, value: Any, status: str) -> str | None:
    """Return a safety flag only for explicitly specified critical thresholds."""
    name = parameter_name.casefold()
    if "critical" in status.casefold():
        return f"{parameter_name or 'A result'} is marked Critical in the report."
    numeric_value = _numeric_value(value)
    if "troponin" in name and "positive" in str(value).casefold():
        return "Troponin is flagged as positive or critical in the report."
    if numeric_value is None:
        return None
    if "hemoglobin" in name and numeric_value < 7:
        return "Hemoglobin is below 7 g/dL in the report."
    if "glucose" in name and (numeric_value < 40 or numeric_value > 600):
        return "Blood glucose is in a critical range in the report."
    if "inr" in name and numeric_value > 4:
        return "INR is above 4 in the report."
    return None


def apply_safety_triage(analysis: dict[str, Any]) -> dict[str, Any]:
    """Add deterministic emergency flags while preserving the provider's extracted facts."""
    biomarker_groups = (
        analysis.get("biomarkers", []),
        analysis.get("abnormal_biomarkers", []),
    )
    flags = list(analysis.get("red_flags", []))
    for biomarkers in biomarker_groups:
        for biomarker in biomarkers:
            if not isinstance(biomarker, dict):
                continue
            flag = _critical_flag(
                str(biomarker.get("parameter_name", "")),
                biomarker.get("value", ""),
                str(biomarker.get("status", "")),
            )
            if flag and flag not in flags:
                flags.append(flag)

    if flags:
        analysis["red_flags"] = flags
    has_critical_value = any(
        _critical_flag(
            str(item.get("parameter_name", "")),
            item.get("value", ""),
            str(item.get("status", "")),
        )
        for group in biomarker_groups
        for item in group
        if isinstance(item, dict)
    )
    if has_critical_value:
        analysis["urgency_level"] = CRITICAL_URGENCY
        analysis["immediate_actions"] = list(dict.fromkeys([
            "Seek urgent in-person medical assessment now; do not rely on this summary alone.",
            *analysis.get("immediate_actions", []),
        ]))
    return analysis
