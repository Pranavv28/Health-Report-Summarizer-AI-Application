"""
app.py — Gradio Blocks UI for the Medical Report Summarizer AI Agent.
Beautiful light-theme design with concise, clean output layout.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

import gradio as gr

from config import SAMPLE_REPORTS, get_active_provider
from medical_summarizer import MedicalSummarizer
from exporter import generate_pdf_report
from schema import HealthReportAnalysis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_summarizer: MedicalSummarizer | None = None


def get_summarizer() -> MedicalSummarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = MedicalSummarizer()
    return _summarizer


# ── Core Handler ──────────────────────────────────────────────────────────────

def summarize_report(
    file_obj: Any,
    text_input: str,
    summary_type: str,
    sample_choice: str,
) -> tuple[str, str, str, str | None, str | None]:
    try:
        summarizer = get_summarizer()
        source: str | bytes | None = None
        file_type = "text"

        if file_obj is not None:
            path = Path(file_obj) if isinstance(file_obj, str) else Path(file_obj.name)
            if path.suffix.lower() == ".pdf":
                source = path.read_bytes()
                file_type = "pdf"
            else:
                source = path.read_text(encoding="utf-8", errors="ignore")
                file_type = "text"
        elif text_input and text_input.strip():
            source = text_input.strip()
            file_type = "text"
        elif sample_choice and sample_choice in SAMPLE_REPORTS:
            source = SAMPLE_REPORTS[sample_choice]
            file_type = "text"
        else:
            return (
                "⚠️ Please upload a file, paste report text, or select a sample report.",
                "", "", None, None,
            )

        result = summarizer.summarize(source, summary_type=summary_type, file_type=file_type)
        summary_data = result["summary"]
        raw_json = result["raw_json"]

        summary_md = _format_summary_markdown(summary_data, summary_type)
        biomarker_md = _format_biomarker_table(summary_data)
        pdf_path = _generate_pdf_download(summary_data)
        json_path = _generate_json_download(raw_json)

        return summary_md, biomarker_md, raw_json, pdf_path, json_path

    except Exception as e:
        logger.error(f"Summarization error: {e}", exc_info=True)
        return f"❌ **Error:** {str(e)}", "", "", None, None


def _format_summary_markdown(data: dict[str, Any], mode: str) -> str:
    """Compact, clean markdown output — never longer than needed."""
    lines: list[str] = []

    title = data.get("report_title", "Health Report Summary")
    lines.append(f"## {title}\n")

    # 1. 📋 PATIENT INFO
    name = data.get("patient_name")
    age = data.get("patient_age")
    gender = data.get("patient_gender")
    date = data.get("test_date")
    patient_bits = []
    if name: patient_bits.append(f"**Name:** {name}")
    if age: patient_bits.append(f"**Age:** {age}")
    if gender: patient_bits.append(f"**Gender:** {gender}")
    if date: patient_bits.append(f"**Date:** {date}")

    if patient_bits:
        lines.append(f"### 📋 PATIENT INFO\n{' &nbsp;·&nbsp; '.join(patient_bits)}\n")

    # Overview text
    overview = data.get("patient_summary", data.get("overview", ""))
    if overview:
        lines.append(f"**Executive Overview:** {overview}\n")

    if mode == "Brief":
        status = data.get("overall_status", "")
        if status:
            emoji = {"Normal": "🟢", "Attention Needed": "🟡", "Urgent Review": "🔴"}.get(status, "⚪")
            lines.append(f"**Overall Clinical Status:** {emoji} {status}\n")

        alerts = data.get("immediate_alerts", [])
        if alerts:
            lines.append("### 🩺 KEY FINDINGS & ALERTS")
            for a in alerts[:5]:
                lines.append(f"- ⚠️ {a}")
            lines.append("")

    elif mode == "Detailed":
        # 2. 🩺 KEY FINDINGS
        findings = data.get("key_findings", [])
        if findings:
            lines.append("### 🩺 KEY FINDINGS")
            for f in findings[:6]:
                lines.append(f"- {f}")
            lines.append("")

        # 3. ⚠️ ABNORMAL VALUES
        biomarkers = data.get("biomarkers", [])
        abnormal_list = [b for b in biomarkers if (b.get("status") if isinstance(b, dict) else b.status).lower() not in ("normal", "optimal")]
        if abnormal_list:
            lines.append("### ⚠️ ABNORMAL VALUES (Flagged)")
            for b in abnormal_list[:8]:
                b_name = b.get("parameter_name") if isinstance(b, dict) else b.parameter_name
                b_val = b.get("value") if isinstance(b, dict) else b.value
                b_unit = b.get("unit") if isinstance(b, dict) else b.unit
                b_ref = b.get("reference_range") if isinstance(b, dict) else b.reference_range
                b_status = b.get("status") if isinstance(b, dict) else b.status
                icon = "🔴" if "high" in b_status.lower() or "critical" in b_status.lower() else "🔵"
                lines.append(f"- {icon} **{b_name}:** {b_val} {b_unit} (*{b_status}* — Ref Range: {b_ref})")
            lines.append("")

        # 4. 💊 MEDICATIONS / TREATMENT
        meds = data.get("medications_or_treatment", [])
        if meds:
            lines.append("### 💊 MEDICATIONS & TREATMENT CONSIDERATIONS")
            for m in meds[:4]:
                lines.append(f"- {m}")
            lines.append("")

        # 5. ✅ RECOMMENDATIONS & DOCTOR QUESTIONS
        questions = data.get("questions_for_doctor", [])
        tips = data.get("lifestyle_wellness_educational_tips", [])
        if questions or tips:
            lines.append("### ✅ RECOMMENDATIONS & DOCTOR QUESTIONS")
            if questions:
                lines.append("**Questions to Ask Your Doctor:**")
                for q in questions[:4]:
                    lines.append(f"- [ ] {q}")
            if tips:
                lines.append("\n**Lifestyle & Wellness Guidance:**")
                for t in tips[:4]:
                    lines.append(f"- 🌱 {t}")
            lines.append("")

    elif mode == "Highlighted":
        # 2. 🩺 KEY FINDINGS / RISK FLAGS
        flags = data.get("risk_flags", [])
        if flags:
            lines.append("### 🩺 KEY FINDINGS & RISK FLAGS")
            for flag in flags[:5]:
                lines.append(f"- 🔴 {flag}")
            lines.append("")

        # 3. ⚠️ ABNORMAL VALUES
        abnormals = data.get("abnormal_biomarkers", [])
        if abnormals:
            lines.append("### ⚠️ ABNORMAL VALUES (Critical Alerts)")
            for b in abnormals[:8]:
                b_name = b.get("parameter_name") if isinstance(b, dict) else b.parameter_name
                b_val = b.get("value") if isinstance(b, dict) else b.value
                b_unit = b.get("unit") if isinstance(b, dict) else b.unit
                b_ref = b.get("reference_range") if isinstance(b, dict) else b.reference_range
                b_status = b.get("status") if isinstance(b, dict) else b.status
                icon = "🔴" if "high" in b_status.lower() or "critical" in b_status.lower() else "🔵"
                lines.append(f"- {icon} **{b_name}:** {b_val} {b_unit} (*{b_status}* — Ref Range: {b_ref})")
            lines.append("")

        # 5. ✅ RECOMMENDATIONS
        actions = data.get("priority_actions", [])
        questions = data.get("questions_for_doctor", [])
        if actions or questions:
            lines.append("### ✅ RECOMMENDATIONS & PRIORITY ACTIONS")
            for action in actions[:4]:
                lines.append(f"- ⚡ {action}")
            for q in questions[:3]:
                lines.append(f"- [ ] Consult Doctor: {q}")

    lines.append("\n---\n*⚕️ AI-generated summary — for educational use only. Consult your doctor.*")
    return "\n".join(lines)


def _format_biomarker_table(data: dict[str, Any]) -> str:
    biomarkers = data.get("biomarkers", data.get("abnormal_biomarkers", []))
    if not biomarkers:
        return "*No biomarker data for this summary mode.*"

    lines = [
        "| Parameter | Value | Unit | Reference Range | Status |",
        "|-----------|-------|------|-----------------|--------|",
    ]
    for b in biomarkers:
        if isinstance(b, dict):
            name, value, unit, ref, status = (
                b.get("parameter_name", ""), b.get("value", ""),
                b.get("unit", ""), b.get("reference_range", ""), b.get("status", ""),
            )
        else:
            name, value, unit, ref, status = b.parameter_name, b.value, b.unit, b.reference_range, b.status

        icon = {"high": "🔴", "low": "🔵", "critical": "⚫", "normal": "🟢"}.get(status.lower(), "⚪")
        lines.append(f"| {name} | {value} | {unit} | {ref} | {icon} {status} |")

    return "\n".join(lines)


def _generate_pdf_download(data: dict[str, Any]) -> str | None:
    """Generate a PDF file and return its temp path for download."""
    try:
        # Ensure required HealthReportAnalysis fields exist (Brief/Highlighted don't have them all)
        pdf_data = {
            "is_valid_report": data.get("is_valid_report", True),
            "unvalid_reason": data.get("unvalid_reason"),
            "report_title": data.get("report_title", "Health Report Summary"),
            "patient_summary": data.get("patient_summary", data.get("overview", "")),
            "biomarkers": data.get("biomarkers", data.get("abnormal_biomarkers", [])),
            "key_findings": data.get("key_findings", data.get("immediate_alerts", data.get("risk_flags", []))),
            "medical_jargon_decoded": data.get("medical_jargon_decoded", []),
            "questions_for_doctor": data.get("questions_for_doctor", []),
            "lifestyle_wellness_educational_tips": data.get("lifestyle_wellness_educational_tips", data.get("priority_actions", [])),
        }
        analysis = HealthReportAnalysis.model_validate(pdf_data)
        pdf_bytes = generate_pdf_report(analysis)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="health_report_")
        tmp.write(pdf_bytes)
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"PDF generation failed: {e}")
        return None


def _generate_json_download(raw_json: str) -> str | None:
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", prefix="health_report_")
        tmp.write(raw_json.encode("utf-8"))
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"JSON file generation failed: {e}")
        return None


def load_sample(sample_name: str) -> str:
    return SAMPLE_REPORTS.get(sample_name, "")


# ── UI ────────────────────────────────────────────────────────────────────────

LIGHT_CSS = """
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body, .gradio-container {
    font-family: 'Inter', sans-serif !important;
    background: #F8FAFC !important;
}

/* ── Header banner ── */
.app-header {
    background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 50%, #06B6D4 100%);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(59,130,246,0.25);
}
.app-header h1 {
    color: #fff !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    margin: 0 0 8px 0 !important;
}
.app-header p {
    color: rgba(255,255,255,0.88) !important;
    font-size: 0.95rem !important;
    margin: 0 !important;
}

/* ── Disclaimer ── */
.disclaimer {
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-left: 4px solid #F97316;
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 18px;
    font-size: 0.84rem;
    color: #9A3412;
}

/* ── Cards ── */
.card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    margin-bottom: 14px;
}

/* ── Section labels ── */
.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748B;
    margin-bottom: 10px;
}

/* ── Primary button ── */
button.primary-btn, .primary-btn {
    background: linear-gradient(135deg, #2563EB, #3B82F6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 12px 0 !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
    transition: all 0.2s ease !important;
}
button.primary-btn:hover {
    box-shadow: 0 6px 20px rgba(37,99,235,0.45) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.tab-nav button {
    font-weight: 500 !important;
    border-radius: 8px 8px 0 0 !important;
}
.tab-nav button.selected {
    color: #2563EB !important;
    border-bottom: 2px solid #2563EB !important;
}

/* ── Provider badge ── */
.provider-badge {
    display: inline-block;
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-top: 8px;
}

/* ── Footer ── */
.app-footer {
    text-align: center;
    color: #94A3B8;
    font-size: 0.8rem;
    padding: 16px 0 4px 0;
    border-top: 1px solid #E2E8F0;
    margin-top: 10px;
}

/* ── Inputs ── */
textarea, input[type="text"] {
    border-radius: 10px !important;
    border: 1px solid #CBD5E1 !important;
    font-size: 0.9rem !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: #3B82F6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}

/* ── Summary output ── */
.output-panel {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
    min-height: 200px;
}
"""


def create_app() -> gr.Blocks:

    try:
        provider = get_active_provider()
        provider_label = {
            "groq": "⚡ Groq AI (Free)",
            "gemini": "✨ Gemini AI (Google)",
            "anthropic": "☁️ Claude AI (Anthropic)",
        }.get(provider, "⚠️ No API key configured")
    except Exception:
        provider_label = "⚠️ Provider not detected"

    with gr.Blocks(
        title="🏥 Medical Report Summarizer — AI",
    ) as demo:

        # ── Header ───────────────────────────────────────────────────────────
        gr.HTML("""
        <div class="app-header">
            <h1 style="display:flex; align-items:center; justify-content:center; gap:12px;">
                <span>🩺</span> Jotform Medical Report AI Agent
            </h1>
            <p>Conversational Healthcare Assistant • Powered by Jotform AI & Gemini Engine</p>
        </div>
        """)

        # ── Disclaimer ───────────────────────────────────────────────────────
        gr.HTML("""
        <div class="disclaimer">
            ⚕️ <strong>Medical Disclaimer:</strong> This Jotform AI Agent is for <em>educational purposes only</em>.
            It does not replace professional medical advice. Always consult a qualified healthcare provider.
        </div>
        """)

        # ── Main Layout ──────────────────────────────────────────────────────
        with gr.Row(equal_height=False):

            # Left: Input Panel
            with gr.Column(scale=1, min_width=320):
                gr.HTML('<div class="card">')
                gr.HTML('<div class="section-label">📄 Input Report</div>')

                file_input = gr.File(
                    label="Upload PDF or TXT",
                    file_types=[".pdf", ".txt"],
                    file_count="single",
                    type="filepath",
                )

                text_input = gr.Textbox(
                    label="Or Paste Report Text",
                    placeholder="Paste your lab report, blood test results, or diagnostic summary here...",
                    lines=7,
                    max_lines=15,
                )

                with gr.Row():
                    sample_dropdown = gr.Dropdown(
                        label="Quick Sample",
                        choices=[""] + list(SAMPLE_REPORTS.keys()),
                        value="",
                        scale=3,
                    )
                    load_sample_btn = gr.Button("Load", variant="secondary", size="sm", scale=1)

                gr.HTML('</div>')

                gr.HTML('<div class="card">')
                gr.HTML('<div class="section-label">⚙️ Summary Mode</div>')

                summary_type = gr.Radio(
                    choices=["Brief", "Detailed", "Highlighted"],
                    value="Brief",
                    label="",
                    info="Brief = quick overview · Detailed = full analysis · Highlighted = abnormal only",
                )

                summarize_btn = gr.Button(
                    "🚀 Analyze Report",
                    variant="primary",
                    size="lg",
                    elem_classes=["primary-btn"],
                )

                gr.HTML(f'<div class="provider-badge">{provider_label}</div>')
                gr.HTML('</div>')

            # Right: Output Panel
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.Tab("📝 Summary"):
                        output_summary = gr.Markdown(
                            value="*Analyze a report to see the summary here.*",
                            elem_classes=["output-panel"],
                        )

                    with gr.Tab("🔬 Biomarkers"):
                        output_biomarkers = gr.Markdown(
                            value="*Biomarker table will appear after analysis.*",
                            elem_classes=["output-panel"],
                        )

                    with gr.Tab("📦 JSON"):
                        output_json = gr.Code(
                            value="",
                            language="json",
                            label="Structured JSON Output",
                            lines=18,
                        )

                with gr.Row():
                    pdf_download = gr.File(label="📥 Download PDF", interactive=False)
                    json_download = gr.File(label="📥 Download JSON", interactive=False)

        # ── Footer ───────────────────────────────────────────────────────────
        gr.HTML("""
        <div class="app-footer">
            Health Report Summarizer AI &nbsp;·&nbsp; Powered by Groq &nbsp;·&nbsp;
            Built by <strong>Pranav Lakhe</strong> &nbsp;·&nbsp; SIT Nagpur
        </div>
        """)

        # ── Events ───────────────────────────────────────────────────────────
        load_sample_btn.click(fn=load_sample, inputs=[sample_dropdown], outputs=[text_input])

        summarize_btn.click(
            fn=summarize_report,
            inputs=[file_input, text_input, summary_type, sample_dropdown],
            outputs=[output_summary, output_biomarkers, output_json, pdf_download, json_download],
        )

    return demo


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    app.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Default(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.slate,
            neutral_hue=gr.themes.colors.slate,
            font=gr.themes.GoogleFont("Inter"),
        ),
        css=LIGHT_CSS,
    )
