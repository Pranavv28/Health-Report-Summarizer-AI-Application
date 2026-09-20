import time
import streamlit as st
import pandas as pd

from config import get_active_provider, SAMPLE_REPORTS
from schema import HealthReportAnalysis, Biomarker
from medical_summarizer import MedicalSummarizer
from exporter import generate_pdf_report

# Page Config
st.set_page_config(
    page_title="Jotform Medical Report AI Agent",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────────────────────
# JOTFORM MEDICAL REPORT AI AGENT DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap');

    :root {
        --jotform-navy:       #0a1526;
        --jotform-dark:       #182436;
        --jotform-orange:     #ff6100;
        --jotform-blue:       #0066ff;
        --jotform-blue-light: #e6f0ff;
        --jotform-teal:       #0d9488;
        --jotform-teal-light: #f0fdfa;
        --bg-main:            #f4f7fb;
        --surface:            #ffffff;
        --surface-low:        #f8fafc;
        --border-light:       #e2e8f0;
        --border-strong:      #cbd5e1;
        --text-dark:          #0f172a;
        --text-muted:         #64748b;
        --emerald-badge:      #059669;
        --amber-badge:        #d97706;
        --rose-badge:         #e11d48;
        --shadow-sm:          0 2px 6px rgba(10,21,38,0.04);
        --shadow-md:          0 10px 30px -5px rgba(10,21,38,0.08);
        --shadow-lg:          0 20px 40px -10px rgba(10,21,38,0.12);
        --radius-sm:          8px;
        --radius-md:          12px;
        --radius-lg:          16px;
        --radius-xl:          24px;
        --font-body:          'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-display:       'Outfit', 'Inter', sans-serif;
    }

    /* ─── Global Reset & Clean Streamlit Overrides ─── */
    html, body, [class*="css"] {
        font-family: var(--font-body);
        color: var(--text-dark);
    }

    .stApp {
        background-color: var(--bg-main) !important;
    }

    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 1400px; }

    /* ─── Top Jotform Navigation Header Bar ─── */
    .jotform-nav {
        background: linear-gradient(135deg, var(--jotform-navy) 0%, #1e293b 100%);
        border-radius: var(--radius-lg);
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: var(--shadow-md);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .jotform-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .jotform-logo-icon {
        width: 42px; height: 42px;
        background: linear-gradient(135deg, var(--jotform-orange) 0%, #ff8533 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        box-shadow: 0 4px 12px rgba(255,97,0,0.35);
    }
    .jotform-brand-title {
        font-family: var(--font-display);
        font-size: 1.35rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .jotform-brand-tag {
        background: var(--jotform-orange);
        color: white;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.08em;
        padding: 3px 8px;
        border-radius: 999px;
        text-transform: uppercase;
    }
    .jotform-brand-subtitle {
        font-size: 0.8rem;
        color: #94a3b8;
        margin: 2px 0 0 0;
    }

    .jotform-status-badges {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .jf-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(4px);
    }
    .jf-badge-active {
        background: rgba(13, 148, 136, 0.2);
        color: #5eead4;
        border-color: rgba(45, 212, 191, 0.3);
    }
    .live-dot {
        width: 8px; height: 8px;
        background: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 10px #10b981;
        animation: pulse-green 1.8s infinite;
    }
    @keyframes pulse-green {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* ─── Jotform Agent Greeting & Hero Card ─── */
    .agent-hero-card {
        background: var(--surface);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-xl);
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: var(--shadow-sm);
        position: relative;
        overflow: hidden;
    }
    .agent-hero-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 5px;
        background: linear-gradient(90deg, var(--jotform-orange) 0%, var(--jotform-blue) 50%, var(--jotform-teal) 100%);
    }

    .agent-profile {
        display: flex;
        align-items: flex-start;
        gap: 18px;
    }
    .agent-avatar {
        width: 56px; height: 56px;
        border-radius: 16px;
        background: linear-gradient(135deg, #0066ff 0%, #0d9488 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        box-shadow: 0 8px 20px rgba(0, 102, 255, 0.25);
        flex-shrink: 0;
        position: relative;
    }
    .agent-avatar-online {
        position: absolute;
        bottom: -2px; right: -2px;
        width: 14px; height: 14px;
        background: #10b981;
        border: 2.5px solid #ffffff;
        border-radius: 50%;
    }
    .agent-meta-name {
        font-family: var(--font-display);
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--jotform-navy);
        margin: 0 0 2px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .agent-meta-role {
        font-size: 0.85rem;
        color: var(--text-muted);
        font-weight: 500;
        margin-bottom: 12px;
    }

    .agent-speech-bubble {
        background: var(--jotform-blue-light);
        border: 1px solid #cce0ff;
        border-radius: 14px;
        padding: 14px 18px;
        font-size: 0.95rem;
        color: #0044b3;
        line-height: 1.6;
        position: relative;
    }

    /* ─── Jotform Card Containers ─── */
    .jotform-card {
        background: var(--surface);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-xl);
        padding: 24px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 20px;
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .jotform-card:hover {
        box-shadow: var(--shadow-md);
        border-color: #cbd5e1;
    }
    .card-title-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border-light);
    }
    .card-title-text {
        font-family: var(--font-display);
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--jotform-navy);
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0;
    }

    /* ─── Stat Metric Chips ─── */
    .stat-box {
        background: var(--surface-low);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-md);
        padding: 16px;
        text-align: left;
    }
    .stat-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    .stat-value {
        font-family: var(--font-display);
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--text-dark);
        line-height: 1;
    }
    .stat-subtext {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 4px;
    }
    .stat-box-elevated { background: #fffbeb; border-color: #fde68a; }
    .stat-box-elevated .stat-label { color: #92400e; }
    .stat-box-elevated .stat-value { color: #b45309; }
    .stat-box-normal { background: #ecfdf5; border-color: #a7f3d0; }
    .stat-box-normal .stat-label { color: #065f46; }
    .stat-box-normal .stat-value { color: #047857; }
    .stat-box-critical { background: #fff1f2; border-color: #fecdd3; }
    .stat-box-critical .stat-label { color: #9f1239; }
    .stat-box-critical .stat-value { color: #be123c; }

    /* ─── Executive Narrative Summary ─── */
    .executive-narrative {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid var(--jotform-blue);
        border-radius: var(--radius-md);
        padding: 18px 20px;
        font-size: 0.96rem;
        color: #334155;
        line-height: 1.65;
    }

    /* ─── Biomarker Card ─── */
    .biomarker-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: var(--radius-md);
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    .biomarker-card:hover {
        border-color: #93c5fd;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.06);
    }
    .biomarker-name {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--jotform-navy);
    }
    .biomarker-value {
        font-family: var(--font-display);
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1;
    }
    .biomarker-unit {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-left: 4px;
    }

    /* Status Badges */
    .badge-normal   { display:inline-flex; align-items:center; gap:4px; padding:3px 12px; border-radius:999px; font-size:11px; font-weight:700; background:#ecfdf5; color:#047857; border:1px solid #a7f3d0; }
    .badge-elevated { display:inline-flex; align-items:center; gap:4px; padding:3px 12px; border-radius:999px; font-size:11px; font-weight:700; background:#fffbeb; color:#b45309; border:1px solid #fde68a; }
    .badge-low      { display:inline-flex; align-items:center; gap:4px; padding:3px 12px; border-radius:999px; font-size:11px; font-weight:700; background:#f0f9ff; color:#0369a1; border:1px solid #bae6fd; }
    .badge-critical { display:inline-flex; align-items:center; gap:4px; padding:3px 12px; border-radius:999px; font-size:11px; font-weight:700; background:#fff1f2; color:#be123c; border:1px solid #fecdd3; }

    /* Visual Range Gauge Bar */
    .gauge-bar {
        width: 100%;
        height: 8px;
        border-radius: 4px;
        background: #e2e8f0;
        display: flex;
        overflow: hidden;
        margin-top: 10px;
    }
    .gauge-seg-low      { background: #7dd3fc; }
    .gauge-seg-normal   { background: #34d399; }
    .gauge-seg-elevated { background: #fbbf24; }
    .gauge-seg-critical { background: #f87171; }
    .gauge-pin-wrap {
        position: relative;
        width: 100%;
        height: 8px;
        margin-top: -2px;
    }
    .gauge-pin {
        position: absolute;
        top: -3px;
        width: 14px; height: 14px;
        border-radius: 50%;
        background: #ffffff;
        border: 2.5px solid #0f172a;
        box-shadow: 0 2px 5px rgba(0,0,0,0.25);
        transform: translateX(-50%);
    }
    .gauge-labels {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 4px;
    }

    /* ─── Jargon Decoder & Doctor Questions Cards ─── */
    .jargon-box {
        background: var(--surface-low);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-md);
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .jargon-term {
        font-size: 0.88rem;
        font-weight: 700;
        color: var(--jotform-blue);
        margin-bottom: 4px;
    }
    .jargon-def { font-size: 0.88rem; color: #334155; margin: 0; line-height: 1.5; }

    .doc-question-card {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        background: var(--surface-low);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-md);
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .doc-question-num {
        width: 26px; height: 26px;
        border-radius: 50%;
        background: var(--jotform-blue-light);
        color: var(--jotform-blue);
        font-weight: 800;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    /* ─── Streamlit UI Controls Customization ─── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: #e2e8f0;
        padding: 4px;
        border-radius: var(--radius-md);
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: var(--radius-sm);
        color: #64748b;
        font-weight: 600;
        font-size: 0.85rem;
        border: none !important;
        padding: 0 16px;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        background: var(--surface) !important;
        color: var(--jotform-blue) !important;
        box-shadow: var(--shadow-sm);
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ─── Radio Button Fix: Force visible label text ─── */
    [data-testid="stRadio"] label {
        color: #334155 !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
        color: #334155 !important;
    }
    /* Selected radio dot colour */
    [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
        border-color: var(--jotform-blue) !important;
        background: var(--jotform-blue) !important;
    }
    /* Summary mode radio row — compact pill style */
    .summary-mode-row [data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row;
        gap: 8px;
        flex-wrap: wrap;
    }
    .summary-mode-row [data-testid="stRadio"] label {
        background: #f1f5f9;
        border: 1.5px solid #e2e8f0;
        border-radius: 999px;
        padding: 5px 16px !important;
        cursor: pointer;
        transition: all 0.15s;
    }
    .summary-mode-row [data-testid="stRadio"] label:has(input:checked) {
        background: var(--jotform-blue-light) !important;
        border-color: var(--jotform-blue) !important;
        color: var(--jotform-blue) !important;
    }

    /* Jotform Orange / Blue Action Buttons */
    .stButton>button {
        background: linear-gradient(135deg, var(--jotform-blue) 0%, #0284c7 100%) !important;
        color: white !important;
        border-radius: var(--radius-md) !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.25) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(0, 102, 255, 0.35) !important;
    }
    /* Primary button extra pop */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #ff6100 0%, #ff8533 100%) !important;
        box-shadow: 0 4px 14px rgba(255,97,0,0.35) !important;
        font-size: 1rem !important;
        padding: 14px 24px !important;
    }
    .stButton>button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(255,97,0,0.5) !important;
    }

    .stDownloadButton>button {
        background: #ffffff !important;
        color: var(--jotform-navy) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: var(--radius-md) !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        padding: 10px 20px !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton>button:hover {
        background: var(--jotform-blue-light) !important;
        border-color: var(--jotform-blue) !important;
        color: var(--jotform-blue) !important;
    }

    [data-testid="stFileUploadDropzone"] {
        background: var(--surface-low) !important;
        border: 2px dashed #cbd5e1 !important;
        border-radius: var(--radius-lg) !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: var(--jotform-blue) !important;
        background: var(--jotform-blue-light) !important;
    }

    /* ─── Sticky Left Intake Panel ─── */
    [data-testid="stHorizontalBlock"] > div:first-child {
        position: sticky;
        top: 1rem;
        align-self: flex-start;
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
        overflow-x: hidden;
        scrollbar-width: thin;
        scrollbar-color: #cbd5e1 transparent;
    }
    [data-testid="stHorizontalBlock"] > div:first-child::-webkit-scrollbar { width: 5px; }
    [data-testid="stHorizontalBlock"] > div:first-child::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }

    /* ─── Empty State Placeholder ─── */
    .empty-agent-state {
        background: var(--surface);
        border: 1px dashed #cbd5e1;
        border-radius: var(--radius-xl);
        padding: 60px 24px;
        text-align: center;
        color: var(--text-muted);
    }
    .empty-agent-icon {
        font-size: 3rem;
        margin-bottom: 12px;
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

import textwrap

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
def st_html(html_str: str, target=st):
    """Render HTML cleanly without markdown converting indented lines into code blocks."""
    clean_lines = [line.strip() for line in html_str.splitlines() if line.strip()]
    target.markdown("\n".join(clean_lines), unsafe_allow_html=True)


def _badge(status: str) -> str:
    s = status.lower()
    if "critical" in s or "abnormal" in s:
        return f'<span class="badge-critical">● {status}</span>'
    elif "high" in s or "elevated" in s or "borderline" in s or "impairment" in s:
        return f'<span class="badge-elevated">▲ {status}</span>'
    elif "low" in s or "decreased" in s:
        return f'<span class="badge-low">▼ {status}</span>'
    else:
        return f'<span class="badge-normal">● {status}</span>'


def _pin_pos(status: str) -> int:
    s = status.lower()
    if "critical" in s:          return 92
    elif "high" in s or "elevated" in s or "borderline" in s or "impairment" in s: return 80
    elif "low" in s or "decreased" in s: return 15
    return 48


def render_biomarker_card(b: Biomarker):
    badge = _badge(b.status)
    pin = _pin_pos(b.status)
    s = b.status.lower()
    val_color = "#be123c" if "critical" in s else "var(--jotform-navy)"

    st_html(f"""
    <div class="biomarker-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
            <div>
                <div class="biomarker-name">{b.parameter_name}</div>
                <div style="display:flex; align-items:baseline; gap:4px; margin-top:2px;">
                    <span class="biomarker-value" style="color:{val_color};">{b.value}</span>
                    <span class="biomarker-unit">{b.unit}</span>
                </div>
            </div>
            {badge}
        </div>

        <div class="gauge-bar">
            <div class="gauge-seg-low"    style="width:25%;"></div>
            <div class="gauge-seg-normal" style="width:35%;"></div>
            <div class="gauge-seg-elevated" style="width:25%;"></div>
            <div class="gauge-seg-critical" style="width:15%;"></div>
        </div>
        <div class="gauge-pin-wrap">
            <div class="gauge-pin" style="left:{pin}%;"></div>
        </div>
        <div class="gauge-labels">
            <span>Reference Range: <strong style="color:#334155;">{b.reference_range}</strong></span>
        </div>

        <div style="margin-top:10px; font-size:0.82rem; color:#475569; line-height:1.5;
                    background:#f8fafc; padding:8px 12px; border-radius:8px;
                    border-left:3px solid #cbd5e1;">
            {b.simple_explanation}
        </div>
    </div>
    """)


# ─────────────────────────────────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────────────────────────────────
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_analysis_time" not in st.session_state:
    st.session_state.last_analysis_time = 0
if "input_text_val" not in st.session_state:
    st.session_state.input_text_val = ""

# Provider detection
active_provider = get_active_provider()
provider_display_name = {
    "groq": "Groq AI (Llama 3.3)",
    "gemini": "Google Gemini 2.0",
    "anthropic": "Claude 3.5 Sonnet",
    "none": "No Provider Configured"
}.get(active_provider, "AI Engine")

if active_provider == "none":
    st.error("⚠️ No AI Provider Configured")
    st.info("Please set `GROQ_API_KEY` (Free tier from https://console.groq.com) or `GEMINI_API_KEY` in your `.env` file.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TOP JOTFORM NAVIGATION BAR
# ─────────────────────────────────────────────────────────────────────────────
st_html(f"""
<div class="jotform-nav">
  <div class="jotform-brand">
    <div class="jotform-logo-icon">🩺</div>
    <div>
      <div class="jotform-brand-title">
        Jotform AI Agents <span class="jotform-brand-tag">MEDICAL AGENT</span>
      </div>
      <p class="jotform-brand-subtitle">Medical Report AI Agent — Conversational Health Diagnostics & Telemetry</p>
    </div>
  </div>
  <div class="jotform-status-badges">
    <span class="jf-badge jf-badge-active"><span class="live-dot"></span> AI Agent Active</span>
    <span class="jf-badge">🔒 HIPAA Compliant</span>
    <span class="jf-badge">⚡ {provider_display_name}</span>
  </div>
</div>
""")


# ─────────────────────────────────────────────────────────────────────────────
# JOTFORM AGENT GREETING & HERO BANNER
# ─────────────────────────────────────────────────────────────────────────────
st_html("""
<div class="agent-hero-card">
  <div class="agent-profile">
    <div class="agent-avatar">
      🤖
      <div class="agent-avatar-online"></div>
    </div>
    <div style="flex-grow:1;">
      <div class="agent-meta-name">
        Medical Report AI Agent
        <span style="font-size:0.75rem; font-weight:600; color:#059669; background:#ecfdf5; padding:2px 8px; border-radius:999px; border:1px solid #a7f3d0;">
          Verified Agent
        </span>
      </div>
      <div class="agent-meta-role">Official Jotform Healthcare Assistant Template</div>
      <div class="agent-speech-bubble">
        👋 <strong>Hello! I'm your Medical Report AI Agent.</strong><br>
        Upload your lab report or select a pre-loaded sample below. I will extract metrics, decode complex medical terminology into plain English, highlight abnormal biomarkers, and generate questions for your doctor consultation.
      </div>
    </div>
  </div>
</div>
""")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN DUAL-PANEL LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
col_intake, col_output = st.columns([1, 1.4], gap="large")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT PANEL: Jotform Agent Data Intake
# ══════════════════════════════════════════════════════════════════════════════
with col_intake:
    st_html("""
    <div class="jotform-card">
        <div class="card-title-bar">
            <h3 class="card-title-text">
                <span>📥</span> Diagnostic Data Ingestion
            </h3>
            <span style="font-size:11px; font-weight:700; color:#0066ff; background:#e6f0ff; padding:3px 10px; border-radius:999px;">
                Agent Intake Form
            </span>
        </div>
    </div>
    """)

    tab_file, tab_text, tab_samples = st.tabs([
        "📤 Upload Report",
        "📝 Paste Text",
        "🧪 Sample Cases"
    ])

    file_to_process = None
    text_to_process = None
    file_type = "text"
    trigger_sample = False

    with tab_file:
        st.markdown("<p style='font-size:0.85rem; color:#64748b; margin:10px 0 8px;'>Upload scanned blood tests, CBC, or metabolic PDFs/Images:</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop your medical report file here",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            help="Files are processed transiently in-memory and never saved to disk."
        )
        if uploaded_file:
            file_to_process = uploaded_file.getvalue()
            ext = uploaded_file.name.split(".")[-1].lower()
            file_type = "pdf" if ext == "pdf" else ("text" if ext == "txt" else ext)
            st.markdown(f"""
            <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:10px; padding:10px 14px; font-size:0.82rem; color:#047857; margin-top:8px;">
                ✓ <strong>{uploaded_file.name}</strong> uploaded successfully.
            </div>""", unsafe_allow_html=True)

    with tab_text:
        st.markdown("<p style='font-size:0.85rem; color:#64748b; margin:10px 0 8px;'>Paste raw medical report text or lab metrics:</p>", unsafe_allow_html=True)
        pasted_text = st.text_area(
            "Report Content Text",
            height=200,
            value=st.session_state.input_text_val,
            placeholder="Paste lab report details here...",
            label_visibility="collapsed"
        )
        if pasted_text.strip():
            text_to_process = pasted_text.strip()
            file_type = "text"

    with tab_samples:
        st.markdown("<p style='font-size:0.85rem; color:#64748b; margin:10px 0 8px;'>Evaluate using pre-configured clinical case studies:</p>", unsafe_allow_html=True)
        sample_choice = st.radio(
            "Choose a sample case study",
            options=list(SAMPLE_REPORTS.keys()),
            label_visibility="collapsed"
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("📋 Load Sample Text", use_container_width=True):
                st.session_state.input_text_val = SAMPLE_REPORTS[sample_choice]
                text_to_process = SAMPLE_REPORTS[sample_choice]
                file_type = "text"
                st.toast(f"Loaded: {sample_choice}", icon="✅")
                st.rerun()
        with col_s2:
            if st.button("⚡ 1-Click Analyze Sample", use_container_width=True):
                text_to_process = SAMPLE_REPORTS[sample_choice]
                file_type = "text"
                trigger_sample = True

    st.markdown("""
    <div style='margin:18px 0 6px; padding:10px 14px; background:#f8fafc;
                border:1px solid #e2e8f0; border-radius:10px;'>
        <p style='font-size:0.78rem; font-weight:700; color:#64748b;
                  text-transform:uppercase; letter-spacing:0.06em; margin:0 0 8px;'>
            📊 Summary Mode
        </p>
    </div>
    """, unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="summary-mode-row">', unsafe_allow_html=True)
        summary_type = st.radio(
            "Summary Mode",
            options=["📋 Detailed", "⚡ Brief", "🚨 Highlighted"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            help="Brief: 1-2 sentences per section | Detailed: Full biomarker analysis | Highlighted: Abnormal & critical alerts only"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    # Strip emoji prefix for backend
    summary_type = summary_type.split(" ", 1)[1] if " " in summary_type else summary_type

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    run_agent_btn = st.button("🚀 Analyze Report", use_container_width=True, type="primary")

    # Trigger analysis if button clicked OR 1-Click Analyze Sample clicked
    if run_agent_btn or trigger_sample:
        input_data = file_to_process if file_to_process else text_to_process
        if not input_data and st.session_state.input_text_val:
            input_data = st.session_state.input_text_val
            file_type = "text"

        if not input_data or (isinstance(input_data, str) and len(input_data.strip()) < 15):
            st.warning("⚠️ Please upload a medical document (PDF/Image scan) or paste lab report text first.")
        else:
            now = time.time()
            if now - st.session_state.last_analysis_time >= 1:
                st.session_state.last_analysis_time = now
                with st.spinner(f"Analyzing report with {summary_type} summary mode..."):
                    try:
                        summarizer = MedicalSummarizer()
                        result = summarizer.summarize(input_data, summary_type=summary_type, file_type=file_type)
                        summary_dict = result["summary"]
                        
                        # Map cleanly into HealthReportAnalysis schema across all 3 modes
                        if summary_type == "Brief":
                            analysis = HealthReportAnalysis(
                                is_valid_report=True,
                                report_title=summary_dict.get("report_title", "Brief Clinical Summary"),
                                patient_name=summary_dict.get("patient_name"),
                                patient_age=summary_dict.get("patient_age"),
                                patient_gender=summary_dict.get("patient_gender"),
                                test_date=summary_dict.get("test_date"),
                                patient_summary=summary_dict.get("overview", ""),
                                key_findings=summary_dict.get("immediate_alerts", []),
                                questions_for_doctor=[]
                            )
                        elif summary_type == "Highlighted":
                            analysis = HealthReportAnalysis(
                                is_valid_report=True,
                                report_title=summary_dict.get("report_title", "Abnormal Findings Highlight"),
                                patient_name=summary_dict.get("patient_name"),
                                patient_age=summary_dict.get("patient_age"),
                                patient_gender=summary_dict.get("patient_gender"),
                                test_date=summary_dict.get("test_date"),
                                patient_summary=summary_dict.get("patient_summary", ""),
                                biomarkers=summary_dict.get("abnormal_biomarkers", []),
                                key_findings=summary_dict.get("risk_flags", []),
                                lifestyle_wellness_educational_tips=summary_dict.get("priority_actions", []),
                                questions_for_doctor=summary_dict.get("questions_for_doctor", [])
                            )
                        else:  # Detailed
                            analysis = HealthReportAnalysis.model_validate(summary_dict)

                        st.session_state.analysis_result = analysis
                        st.session_state.chat_history = []
                        st.success(f"✅ {summary_type} Analysis Complete!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"❌ Analysis Failed: {str(err) or repr(err)}")
                        st.info("💡 Tip: Ensure your PDF is not password-protected and contains readable laboratory text or values.")

    st.markdown(f"""
    <div style="font-size:11px; color:#94a3b8; text-align:center; margin-top:16px;">
        Powered by Jotform Agent Builder & {provider_display_name} Engine
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL: Jotform Agent Results & Studio
# ══════════════════════════════════════════════════════════════════════════════
with col_output:
    analysis: HealthReportAnalysis = st.session_state.analysis_result

    if not analysis:
        st_html("""
        <div class="empty-agent-state">
            <div class="empty-agent-icon">🤖🩺</div>
            <h4 style="font-family:var(--font-display); font-size:1.2rem; color:var(--jotform-navy); margin:0 0 6px;">
                Ready for Medical Data Ingestion
            </h4>
            <p style="font-size:0.9rem; color:#64748b; max-width:400px; margin:0 auto;">
                Select a sample case study or upload a medical PDF/scan on the left panel, pick a summary type (Brief, Detailed, or Highlighted), and click Analyze Report.
            </p>
        </div>
        """)

    elif not analysis.is_valid_report:
        st_html(f"""
        <div class="jotform-card" style="border-left:4px solid var(--rose-badge); background:#fff1f2;">
            <h4 style="color:#be123c; margin:0 0 6px; font-family:var(--font-display); font-weight:700;">
                ⚠️ Invalid Medical Document
            </h4>
            <p style="color:#9f1239; margin:0; font-size:0.9rem;">
                {analysis.unvalid_reason or "The uploaded file does not appear to be a recognized medical lab report or health document."}
            </p>
            <p style="color:#64748b; margin-top:8px; font-size:0.82rem;">
                Please ensure you upload a diagnostic blood test, CBC, metabolic panel, or physician report.
            </p>
        </div>
        """)

    else:
        # ── 1. 📋 PATIENT INFO (if present) ──
        p_bits = []
        if analysis.patient_name: p_bits.append(f"<strong>Patient:</strong> {analysis.patient_name}")
        if analysis.patient_age: p_bits.append(f"<strong>Age:</strong> {analysis.patient_age}")
        if analysis.patient_gender: p_bits.append(f"<strong>Gender:</strong> {analysis.patient_gender}")
        if analysis.test_date: p_bits.append(f"<strong>Date:</strong> {analysis.test_date}")

        if p_bits:
            st_html(f"""
            <div style="background:#f0f9ff; border:1px solid #bae6fd; border-radius:12px; padding:10px 16px; margin-bottom:14px; font-size:0.88rem; color:#0369a1; display:flex; gap:16px; flex-wrap:wrap;">
                <span>📋 {' &nbsp;·&nbsp; '.join(p_bits)}</span>
            </div>
            """)

        # Metrics Summary Bar
        total = len(analysis.biomarkers)
        abnormal_list = [b for b in analysis.biomarkers if b.status.lower() not in ("normal", "optimal")]
        abnormal = len(abnormal_list)
        normal_count = total - abnormal
        critical_count = sum(1 for b in analysis.biomarkers if "critical" in b.status.lower())

        c1, c2, c3, c4 = st.columns(4)
        st_html(f"""
        <div class="stat-box">
            <div class="stat-label">Total Markers</div>
            <div class="stat-value">{total}</div>
            <div class="stat-subtext">Extracted metrics</div>
        </div>""", target=c1)

        st_html(f"""
        <div class="stat-box {'stat-box-elevated' if abnormal else 'stat-box-normal'}">
            <div class="stat-label">Flagged / High</div>
            <div class="stat-value">{abnormal}</div>
            <div class="stat-subtext">Require review</div>
        </div>""", target=c2)

        st_html(f"""
        <div class="stat-box stat-box-normal">
            <div class="stat-label">Optimal Range</div>
            <div class="stat-value">{normal_count}</div>
            <div class="stat-subtext">Physiologically normal</div>
        </div>""", target=c3)

        st_html(f"""
        <div class="stat-box {'stat-box-critical' if critical_count else 'stat-box-normal'}">
            <div class="stat-label">Critical Concern</div>
            <div class="stat-value">{critical_count}</div>
            <div class="stat-subtext">Urgent review</div>
        </div>""", target=c4)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # Executive Summary Narrative
        st_html(f"""
        <div class="jotform-card">
            <div class="card-title-bar">
                <h3 class="card-title-text">
                    <span>📋</span> Executive Diagnostic Synthesis
                </h3>
                <span class="badge-elevated">{analysis.report_title or 'Health Report Summary'}</span>
            </div>
            <div class="executive-narrative">
                {analysis.patient_summary}
            </div>
        </div>
        """)

        # Tabbed Views: Structured Sections
        out_tab1, out_tab2, out_tab3, out_tab4, out_tab5 = st.tabs([
            "⚠️ Abnormal Values",
            "🩺 Key Findings",
            "🔬 Biomarker Telemetry",
            "💊 Treatment & Guidance",
            "🤖 Ask AI Agent"
        ])

        with out_tab1:
            st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#b91c1c; margin-bottom:10px;'>⚠️ Flagged Abnormal Biomarkers (Require Clinical Attention):</p>", unsafe_allow_html=True)
            if abnormal_list:
                for b in abnormal_list:
                    render_biomarker_card(b)
            else:
                st.success("✅ All analyzed biomarkers are within physiological reference intervals.")

        with out_tab2:
            st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#0f172a; margin-bottom:8px;'>🩺 Primary Clinical Findings:</p>", unsafe_allow_html=True)
            if analysis.key_findings:
                for finding in analysis.key_findings:
                    st_html(f"""
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 16px; margin-bottom:8px; font-size:0.9rem; color:#334155; display:flex; gap:10px;">
                        <span style="color:#0066ff;">📌</span> <span>{finding}</span>
                    </div>""")
            else:
                st.info("No key findings reported.")

        with out_tab3:
            st.markdown("<p style='font-size:0.85rem; color:#64748b; margin-bottom:12px;'>All extracted metrics calibrated against clinical reference intervals:</p>", unsafe_allow_html=True)
            if analysis.biomarkers:
                for b in analysis.biomarkers:
                    render_biomarker_card(b)
                with st.expander("📋 View Data Table"):
                    rows = [{"Parameter": b.parameter_name, "Value": f"{b.value} {b.unit}".strip(),
                             "Reference Range": b.reference_range, "Status": b.status,
                             "Explanation": b.simple_explanation} for b in analysis.biomarkers]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No numerical biomarkers detected in this report.")

            if analysis.medical_jargon_decoded:
                st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#0f172a; margin:16px 0 8px;'>📖 Medical Jargon Decoded:</p>", unsafe_allow_html=True)
                for item in analysis.medical_jargon_decoded:
                    st_html(f"""
                    <div class="jargon-box">
                        <div class="jargon-term">ℹ️ {item.term}</div>
                        <p class="jargon-def">{item.plain_english}</p>
                    </div>""")

        with out_tab4:
            # 💊 Medications / Treatment
            if analysis.medications_or_treatment:
                st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#0f172a; margin-bottom:8px;'>💊 Medications & Clinical Treatment Considerations:</p>", unsafe_allow_html=True)
                for med in analysis.medications_or_treatment:
                    st_html(f"""
                    <div style="background:#fefce8; border:1px solid #fef08a; border-left:4px solid #eab308; border-radius:10px; padding:12px 16px; margin-bottom:8px; font-size:0.88rem; color:#854d0e; display:flex; gap:10px;">
                        <span>💊</span> <span>{med}</span>
                    </div>""")

            # ✅ Recommendations & Doctor Questions
            if analysis.lifestyle_wellness_educational_tips:
                st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#0f172a; margin:14px 0 8px;'>✅ Actionable Wellness Recommendations:</p>", unsafe_allow_html=True)
                for tip in analysis.lifestyle_wellness_educational_tips:
                    st_html(f"""
                    <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-left:4px solid #059669; border-radius:10px; padding:12px 16px; margin-bottom:8px; font-size:0.88rem; color:#047857; display:flex; gap:10px;">
                        <span>🌱</span> <span>{tip}</span>
                    </div>""")

            if analysis.questions_for_doctor:
                st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#0f172a; margin:14px 0 8px;'>🩺 Questions to Ask Your Doctor:</p>", unsafe_allow_html=True)
                for idx, q in enumerate(analysis.questions_for_doctor, 1):
                    st_html(f"""
                    <div class="doc-question-card">
                        <div class="doc-question-num">{idx}</div>
                        <div style="font-size:0.9rem; color:#0f172a; line-height:1.5;">{q}</div>
                    </div>""")

        with out_tab5:
            st.markdown("<p style='font-size:0.85rem; color:#64748b; margin-bottom:12px;'>Chat directly with your Jotform Medical AI Agent about your results:</p>", unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            user_q = st.chat_input("Ask a follow-up question (e.g. 'How can I lower my LDL cholesterol?')")
            if user_q:
                st.session_state.chat_history.append({"role": "user", "content": user_q})
                with st.chat_message("user"):
                    st.write(user_q)
                with st.chat_message("assistant"):
                    with st.spinner("Jotform Medical Agent is formulating response..."):
                        summarizer = MedicalSummarizer()
                        ctx = f"Report Title: {analysis.report_title}\nSummary: {analysis.patient_summary}\nFindings: {analysis.key_findings}"
                        reply = summarizer.answer_health_question(
                            report_summary=ctx,
                            user_question=user_q,
                            chat_history=st.session_state.chat_history
                        )
                        st.write(reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": reply})

        # ── EXPORT ACTION BUTTONS ──
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#334155; margin-bottom:8px;'>📥 Export Report Data:</p>", unsafe_allow_html=True)
        ex_col1, ex_col2, ex_col3 = st.columns(3)
        with ex_col1:
            try:
                pdf_bytes = generate_pdf_report(analysis)
                st.download_button(
                    label="📥 Export as PDF",
                    data=pdf_bytes,
                    file_name="Medical_Report_Summary.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as pdf_err:
                st.error(f"PDF download error: {pdf_err}")
        with ex_col2:
            json_bytes = analysis.model_dump_json(indent=2)
            st.download_button(
                label="📋 Export as JSON",
                data=json_bytes,
                file_name="Medical_Report_Data.json",
                mime="application/json",
                use_container_width=True
            )
        with ex_col3:
            md_lines = [f"# {analysis.report_title}\n", f"## Patient Summary\n{analysis.patient_summary}\n"]
            if analysis.key_findings:
                md_lines.append("## Key Findings\n" + "\n".join(f"- {f}" for f in analysis.key_findings))
            if analysis.questions_for_doctor:
                md_lines.append("\n## Doctor Questions\n" + "\n".join(f"- {q}" for q in analysis.questions_for_doctor))
            st.download_button(
                label="📝 Export as Markdown",
                data="\n".join(md_lines),
                file_name="Medical_Report_Summary.md",
                mime="text/markdown",
                use_container_width=True
            )

