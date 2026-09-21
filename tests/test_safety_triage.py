"""Tests for deterministic report-based emergency escalation."""

from safety_triage import CRITICAL_URGENCY, apply_safety_triage


def test_critical_hemoglobin_escalates_to_emergency() -> None:
    """A report explicitly showing severe anemia must trigger escalation."""
    result = apply_safety_triage({
        "biomarkers": [
            {"parameter_name": "Hemoglobin", "value": "6.8", "status": "Low"}
        ],
        "immediate_actions": ["Contact the ordering clinician."],
    })

    assert result["urgency_level"] == CRITICAL_URGENCY
    assert "Hemoglobin is below 7 g/dL in the report." in result["red_flags"]
    assert result["immediate_actions"][0].startswith("Seek urgent in-person")


def test_noncritical_result_preserves_existing_urgency() -> None:
    """Routine findings must not be escalated by the deterministic rules."""
    result = apply_safety_triage({
        "urgency_level": "Routine",
        "biomarkers": [
            {"parameter_name": "Hemoglobin", "value": "14.2", "status": "Normal"}
        ],
    })

    assert result["urgency_level"] == "Routine"
    assert "red_flags" not in result


def test_critical_glucose_is_detected_from_abnormal_summary() -> None:
    """Highlighted summaries also receive emergency protection."""
    result = apply_safety_triage({
        "abnormal_biomarkers": [
            {"parameter_name": "Fasting Blood Glucose", "value": "620 mg/dL", "status": "High"}
        ]
    })

    assert result["urgency_level"] == CRITICAL_URGENCY
    assert "Blood glucose is in a critical range in the report." in result["red_flags"]
