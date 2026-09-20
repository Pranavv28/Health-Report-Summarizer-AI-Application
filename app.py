"""
app.py — Gradio Blocks UI for the Automated Medical Report Summarization Agent.

Features:
- File upload (PDF/TXT) and text paste input
- Three summary modes: Brief, Detailed, Highlighted
- Built-in sample report quick-loader
- Interactive biomarker table, summary display, and JSON viewer
- PDF & JSON export downloads
- Medical disclaimer notice
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

# ──────────────────────────────────────────────
# Global summarizer instance (lazy-loaded)
# ──────────────────────────────────────────────
_summarizer: MedicalSummarizer | None = None


def get_summarizer() -> MedicalSummarizer:
    """Lazy-load the MedicalSummarizer singleton."""
    global _summarizer
    if _summarizer is None:
        _summarizer = MedicalSummarizer()
    return _summarizer


# ──────────────────────────────────────────────
# Core handler functions
# ──────────────────────────────────────────────


def summarize_report(
    file_obj: Any,
    text_input: str,
    summary_type: str,
    sample_choice: str,
) -> tuple[str, str, str, str | None, str | None]:
    """
    Main summarization handler for the Gradio UI.

    Returns:
        Tuple of (summary_markdown, biomarker_table_md, json_export, pdf_path, json_path)
    """
    try:
        summarizer = get_summarizer()

        # Determine input source priority: file > text > sample
        source: str | bytes | None = None
        file_type = "text"

        if file_obj is not None:
            # Gradio file upload — file_obj is a file path string
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
                "⚠️ **No input provided.** Please upload a file, paste report text, or select a sample report.",
                "",
                "",
                None,
                None,
            )

        # Run summarization
        result = summarizer.summarize(source, summary_type=summary_type, file_type=file_type)
        summary_data = result["summary"]
        raw_json = result["raw_json"]

        # Format outputs
        summary_md = _format_summary_markdown(summary_data, summary_type)
        biomarker_md = _format_biomarker_table(summary_data)

        # Generate downloadable files
        pdf_path = _generate_pdf_download(summary_data)
        json_path = _generate_json_download(raw_json)

        return summary_md, biomarker_md, raw_json, pdf_path, json_path

    except Exception as e:
        logger.error(f"Summarization error: {e}", exc_info=True)
        error_msg = f"❌ **Error:** {str(e)}"
        return error_msg, "", "", None, None


def _format_summary_markdown(data: dict[str, Any], mode: str) -> str:
    """Format the summary data into readable Markdown."""
    lines: list[str] = []

    title = data.get("report_title", "Health Report Summary")
    lines.append(f"# 🏥 {title}\n")

    # Brief mode
    if mode == "Brief":
        overview = data.get("overview", data.get("patient_summary", ""))
        if overview:
            lines.append(f"**Overview:** {overview}\n")

        status = data.get("overall_status", "")
        if status:
            emoji = {"Normal": "🟢", "Attention Needed": "🟡", "Urgent Review": "🔴"}.get(
                status, "⚪"
            )
            lines.append(f"**Status:** {emoji} {status}\n")

        alerts = data.get("immediate_alerts", [])
        if alerts:
            lines.append("### ⚠️ Immediate Alerts\n")
            for alert in alerts:
                lines.append(f"- {alert}")
            lines.append("")

    # Detailed mode
    elif mode == "Detailed":
        summary = data.get("patient_summary", "")
        if summary:
            lines.append(f"**Patient Summary:** {summary}\n")

        findings = data.get("key_findings", [])
        if findings:
            lines.append("### 🔍 Key Findings\n")
            for f in findings:
                lines.append(f"- {f}")
            lines.append("")

        jargon = data.get("medical_jargon_decoded", [])
        if jargon:
            lines.append("### 📖 Medical Terms Decoded\n")
            for item in jargon:
                term = item.get("term", "") if isinstance(item, dict) else item.term
                meaning = (
                    item.get("plain_english", "") if isinstance(item, dict) else item.plain_english
                )
                lines.append(f"- **{term}:** {meaning}")
            lines.append("")

        questions = data.get("questions_for_doctor", [])
        if questions:
            lines.append("### 🩺 Questions for Your Doctor\n")
            for q in questions:
                lines.append(f"- ☐ {q}")
            lines.append("")

        tips = data.get("lifestyle_wellness_educational_tips", [])
        if tips:
            lines.append("### 💡 Lifestyle & Wellness Tips\n")
            for tip in tips:
                lines.append(f"- {tip}")
            lines.append("")

    # Highlighted mode
    elif mode == "Highlighted":
        summary = data.get("patient_summary", "")
        if summary:
            lines.append(f"**Summary:** {summary}\n")

        flags = data.get("risk_flags", [])
        if flags:
            lines.append("### 🚩 Risk Flags\n")
            for flag in flags:
                lines.append(f"- 🔴 {flag}")
            lines.append("")

        actions = data.get("priority_actions", [])
        if actions:
            lines.append("### ✅ Priority Actions\n")
            for action in actions:
                lines.append(f"- {action}")
            lines.append("")

        questions = data.get("questions_for_doctor", [])
        if questions:
            lines.append("### 🩺 Questions for Your Doctor\n")
            for q in questions:
                lines.append(f"- ☐ {q}")
            lines.append("")

    # Disclaimer
    lines.append("---")
    lines.append(
        "*⚕️ **Disclaimer:** This AI-generated summary is for educational and informational "
        "purposes only. It is not a substitute for professional medical advice, diagnosis, "
        "or treatment.*"
    )

    return "\n".join(lines)


def _format_biomarker_table(data: dict[str, Any]) -> str:
    """Format biomarkers into a Markdown table."""
    biomarkers = data.get("biomarkers", data.get("abnormal_biomarkers", []))
    if not biomarkers:
        return "*No biomarker data available for this summary mode.*"

    lines = [
        "| Parameter | Value | Unit | Reference Range | Status |",
        "|-----------|-------|------|-----------------|--------|",
    ]

    for b in biomarkers:
        if isinstance(b, dict):
            name = b.get("parameter_name", "")
            value = b.get("value", "")
            unit = b.get("unit", "")
            ref = b.get("reference_range", "")
            status = b.get("status", "")
        else:
            name, value, unit, ref, status = (
                b.parameter_name,
                b.value,
                b.unit,
                b.reference_range,
                b.status,
            )

        # Status emoji
        status_display = status
        if status.lower() in ("high", "elevated"):
            status_display = f"🔴 {status}"
        elif status.lower() in ("low", "decreased"):
            status_display = f"🔵 {status}"
        elif status.lower() in ("critical", "abnormal"):
            status_display = f"⚫ {status}"
        elif status.lower() == "normal":
            status_display = f"🟢 {status}"

        lines.append(f"| {name} | {value} | {unit} | {ref} | {status_display} |")

    return "\n".join(lines)


def _generate_pdf_download(data: dict[str, Any]) -> str | None:
    """Generate a PDF file and return its temp path for download."""
    try:
        analysis = HealthReportAnalysis.model_validate(data)
        pdf_bytes = generate_pdf_report(analysis)

        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", prefix="health_report_"
        )
        tmp.write(pdf_bytes)
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"PDF generation failed: {e}")
        return None


def _generate_json_download(raw_json: str) -> str | None:
    """Save JSON export to a temp file for download."""
    try:
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".json", prefix="health_report_"
        )
        tmp.write(raw_json.encode("utf-8"))
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"JSON file generation failed: {e}")
        return None


def load_sample(sample_name: str) -> str:
    """Load a sample report into the text input."""
    if sample_name and sample_name in SAMPLE_REPORTS:
        return SAMPLE_REPORTS[sample_name]
    return ""


# ──────────────────────────────────────────────
# Gradio UI Definition
# ──────────────────────────────────────────────

def create_app() -> gr.Blocks:
    """Build and return the Gradio Blocks application."""

    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    )

    with gr.Blocks(
        title="🏥 Medical Report Summarizer — AI Agent",
        theme=theme,
        css="""
        .disclaimer-box {
            background: #FEF2F2;
            border: 1px solid #FECACA;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 16px;
            font-size: 0.85em;
            color: #991B1B;
        }
        .header-section {
            text-align: center;
            padding: 20px 0 10px 0;
        }
        """,
    ) as demo:

        # Header
        gr.Markdown(
            """
            <div class="header-section">

            # 🏥 Automated Medical Report Summarization Agent

            Upload a medical report (PDF or text) and get an AI-powered, structured health summary
            with biomarker analysis, risk flags, doctor questions, and export options.

            </div>
            """,
        )

        # Disclaimer
        gr.HTML(
            '<div class="disclaimer-box">'
            "⚕️ <strong>Medical Disclaimer:</strong> This tool is for <em>educational and "
            "informational purposes only</em>. It is not a substitute for professional medical "
            "advice, diagnosis, or treatment. Always consult a qualified healthcare provider."
            "</div>"
        )

        with gr.Row():
            # Left column: Inputs
            with gr.Column(scale=1):
                gr.Markdown("### 📄 Input Report")

                file_input = gr.File(
                    label="Upload Report (PDF or TXT)",
                    file_types=[".pdf", ".txt", ".text"],
                    file_count="single",
                    type="filepath",
                )

                text_input = gr.Textbox(
                    label="Or Paste Report Text",
                    placeholder="Paste your medical report text here...",
                    lines=8,
                    max_lines=20,
                )

                sample_dropdown = gr.Dropdown(
                    label="🧪 Quick Load Sample Report",
                    choices=[""] + list(SAMPLE_REPORTS.keys()),
                    value="",
                    interactive=True,
                )

                load_sample_btn = gr.Button("📋 Load Sample", variant="secondary", size="sm")

                summary_type = gr.Radio(
                    choices=["Brief", "Detailed", "Highlighted"],
                    value="Detailed",
                    label="Summary Mode",
                )

                summarize_btn = gr.Button(
                    "🚀 Summarize Report", variant="primary", size="lg"
                )

                # Provider info
                try:
                    provider = get_active_provider()
                    provider_label = {
                        "anthropic": "☁️ Claude AI (Anthropic)",
                        "gemini": "✨ Gemini AI (Google)",
                        "none": "⚠️ No API key configured",
                    }.get(provider, provider)
                except Exception:
                    provider_label = "⚠️ Provider not detected"

                gr.Markdown(f"**Active AI Provider:** {provider_label}")

            # Right column: Outputs
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Analysis Results")

                with gr.Tabs():
                    with gr.Tab("📝 Summary"):
                        output_summary = gr.Markdown(
                            value="*Upload a report or load a sample to get started.*",
                            label="Summary",
                        )

                    with gr.Tab("🔬 Biomarkers"):
                        output_biomarkers = gr.Markdown(
                            value="*Biomarker table will appear here after analysis.*",
                            label="Biomarkers",
                        )

                    with gr.Tab("📦 JSON Export"):
                        output_json = gr.Code(
                            value="",
                            language="json",
                            label="Structured JSON Output",
                            lines=20,
                        )

                with gr.Row():
                    pdf_download = gr.File(
                        label="📥 Download PDF Report",
                        interactive=False,
                    )
                    json_download = gr.File(
                        label="📥 Download JSON Export",
                        interactive=False,
                    )

        # ── Event Handlers ──

        load_sample_btn.click(
            fn=load_sample,
            inputs=[sample_dropdown],
            outputs=[text_input],
        )

        summarize_btn.click(
            fn=summarize_report,
            inputs=[file_input, text_input, summary_type, sample_dropdown],
            outputs=[output_summary, output_biomarkers, output_json, pdf_download, json_download],
        )

        # Footer
        gr.Markdown(
            """
            ---
            **Built with** Gradio + Claude AI | **Project:** Health Report Summarizer AI Application
            | **Author:** Pranav Lakhe (SIT Nagpur)
            """,
        )

    return demo


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    app.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
    )
