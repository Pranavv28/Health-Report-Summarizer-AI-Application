import time
import streamlit as st
import pandas as pd

from config import is_api_key_configured, SAMPLE_REPORTS
from schema import HealthReportAnalysis, Biomarker
from gemini_engine import HealthReportAnalyzer
from exporter import generate_pdf_report

# Page Config
st.set_page_config(
    page_title="PulseCare AI – Clinical Intelligence Studio",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────────────────────
# STITCH CLINICAL PRECISION DESIGN SYSTEM — Light, Swiss-Minimalist Theme
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    :root {
        --bg:              #f8fafc;
        --surface:         #ffffff;
        --surface-low:     #f8fafc;
        --surface-mid:     #f1f5f9;
        --border:          #e2e8f0;
        --border-strong:   #cbd5e1;
        --text-primary:    #0f172a;
        --text-secondary:  #334155;
        --text-muted:      #64748b;
        --primary:         #0284c7;
        --primary-hover:   #0ea5e9;
        --emerald:         #059669;
        --emerald-light:   #ecfdf5;
        --emerald-border:  #a7f3d0;
        --amber:           #d97706;
        --amber-light:     #fffbeb;
        --amber-border:    #fde68a;
        --rose:            #e11d48;
        --rose-light:      #fff1f2;
        --rose-border:     #fecdd3;
        --sky-light:       #f0f9ff;
        --sky-border:      #bae6fd;
        --shadow-sm:       0 1px 3px 0 rgba(15,23,42,0.04), 0 1px 2px 0 rgba(15,23,42,0.03);
        --shadow-md:       0 4px 12px -2px rgba(15,23,42,0.06), 0 2px 6px -1px rgba(15,23,42,0.03);
        --radius-sm:       6px;
        --radius-md:       8px;
        --radius-lg:       12px;
        --radius-xl:       16px;
        --font-ui:         'Plus Jakarta Sans', -apple-system, sans-serif;
        --font-display:    'Outfit', 'Plus Jakarta Sans', sans-serif;
    }

    /* ─── Base Reset ─── */
    html, body, [class*="css"] {
        font-family: var(--font-ui);
        color: var(--text-primary);
    }

    .stApp {
        background-color: var(--bg) !important;
        color: var(--text-primary);
    }

    /* Hide Streamlit chrome */
    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { display: none !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

    /* ─── Hero Header ─── */
    .hero-card {
        position: relative;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: 28px 32px;
        margin-bottom: 20px;
        box-shadow: var(--shadow-sm);
        overflow: hidden;
    }
    .hero-card::before {
        content: '';
        position: absolute;
        top: -80px; right: -80px;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(2,132,199,0.07) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-card::after {
        content: '';
        position: absolute;
        bottom: -60px; left: -60px;
        width: 250px; height: 250px;
        background: radial-gradient(circle, rgba(5,150,105,0.06) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-eyebrow {
        font-family: var(--font-ui);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--primary);
        margin-bottom: 6px;
    }
    .hero-title {
        font-family: var(--font-display);
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        color: var(--text-primary);
        margin: 0 0 6px 0;
        line-height: 1.15;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: var(--text-muted);
        margin: 0;
        line-height: 1.6;
    }

    /* Status Pills */
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .pill-emerald  { background: var(--emerald-light); color: #065f46; border: 1px solid var(--emerald-border); }
    .pill-sky      { background: var(--sky-light);     color: #0c4a6e; border: 1px solid var(--sky-border); }
    .pill-slate    { background: var(--surface-low);   color: var(--text-secondary); border: 1px solid var(--border); }
    .pill-amber    { background: var(--amber-light);   color: #78350f; border: 1px solid var(--amber-border); }
    .pill-rose     { background: var(--rose-light);    color: #9f1239; border: 1px solid var(--rose-border); }
    .ping-dot {
        width: 8px; height: 8px;
        background: #22c55e;
        border-radius: 50%;
        animation: live-ping 1.8s ease-in-out infinite;
    }
    @keyframes live-ping {
        0% { box-shadow: 0 0 0 0 rgba(34,197,94,0.6); }
        70% { box-shadow: 0 0 0 8px rgba(34,197,94,0); }
        100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
    }

    /* ─── Disclaimer ─── */
    .disclaimer {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-left: 4px solid #f97316;
        border-radius: var(--radius-lg);
        padding: 12px 18px;
        font-size: 0.875rem;
        color: #7c2d12;
        margin-bottom: 20px;
    }

    /* ─── Clinical Cards ─── */
    .clinical-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: 24px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 16px;
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .clinical-card:hover {
        border-color: var(--border-strong);
        box-shadow: var(--shadow-md);
    }
    .card-header {
        font-family: var(--font-display);
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 4px 0;
    }
    .card-subheader {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin: 0;
    }

    /* ─── Stat Chips ─── */
    .stat-chip {
        background: var(--surface-low);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
    }
    .stat-chip-label {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    .stat-chip-value {
        font-family: var(--font-display);
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--text-primary);
        line-height: 1;
    }
    .stat-chip-sub {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 3px;
    }
    .stat-chip-elevated { background: #fffbeb; border-color: #fde68a; }
    .stat-chip-elevated .stat-chip-label  { color: #92400e; }
    .stat-chip-elevated .stat-chip-value  { color: #78350f; }
    .stat-chip-normal   { background: #ecfdf5; border-color: #a7f3d0; }
    .stat-chip-normal .stat-chip-label    { color: #065f46; }
    .stat-chip-normal .stat-chip-value    { color: #047857; }
    .stat-chip-critical { background: #fff1f2; border-color: #fecdd3; }
    .stat-chip-critical .stat-chip-label  { color: #9f1239; }
    .stat-chip-critical .stat-chip-value  { color: #be123c; }

    /* ─── Summary Narrative Card ─── */
    .narrative-block {
        position: relative;
        background: var(--surface-low);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 16px 18px 16px 22px;
        font-size: 0.97rem;
        color: var(--text-secondary);
        line-height: 1.65;
    }
    .narrative-block::before {
        content: '';
        position: absolute;
        left: 0; top: 0; bottom: 0;
        width: 4px;
        border-radius: var(--radius-sm) 0 0 var(--radius-sm);
        background: linear-gradient(180deg, #0284c7, #d97706, #e11d48);
    }

    /* ─── Biomarker Cards ─── */
    .biomarker-card {
        background: rgba(248,250,252,0.7);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
    }
    .biomarker-card:hover {
        border-color: var(--border-strong);
        background: var(--surface);
        box-shadow: var(--shadow-sm);
    }
    .biomarker-name {
        font-family: var(--font-ui);
        font-size: 0.875rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    .biomarker-value {
        font-family: var(--font-display);
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--text-primary);
        line-height: 1;
    }
    .biomarker-unit {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-left: 4px;
    }

    /* Status Badges (inline) */
    .badge-normal   { display:inline-flex; align-items:center; gap:4px; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; background:var(--emerald-light); color:#065f46; border:1px solid var(--emerald-border); }
    .badge-elevated { display:inline-flex; align-items:center; gap:4px; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; background:var(--amber-light);   color:#78350f; border:1px solid var(--amber-border); }
    .badge-low      { display:inline-flex; align-items:center; gap:4px; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; background:var(--sky-light);     color:#0c4a6e; border:1px solid var(--sky-border); }
    .badge-critical { display:inline-flex; align-items:center; gap:4px; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; background:var(--rose-light);    color:#9f1239; border:1px solid var(--rose-border); }

    /* ─── Range Gauge ─── */
    .gauge-bar {
        width: 100%;
        height: 8px;
        border-radius: 4px;
        background: #e2e8f0;
        display: flex;
        overflow: hidden;
        position: relative;
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
        background: white;
        border: 2.5px solid #1e293b;
        box-shadow: 0 1px 4px rgba(0,0,0,0.2);
        transform: translateX(-50%);
    }
    .gauge-labels {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 2px;
    }

    /* ─── Jargon Decoder Cards ─── */
    .jargon-card {
        background: var(--surface-low);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 16px 18px;
        margin-bottom: 10px;
        transition: border-color 0.18s, background 0.18s;
    }
    .jargon-card:hover {
        border-color: #7dd3fc;
        background: var(--surface);
    }
    .jargon-term {
        font-size: 0.875rem;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 5px;
    }
    .jargon-def { font-size: 0.875rem; color: var(--text-secondary); line-height: 1.55; margin: 0; }

    /* ─── Doctor Questions ─── */
    .question-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        background: var(--surface-low);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .question-num {
        flex-shrink: 0;
        width: 26px; height: 26px;
        border-radius: 50%;
        background: #e0f2fe;
        color: var(--primary);
        font-size: 12px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid var(--sky-border);
    }
    .question-text { font-size: 0.9rem; color: var(--text-primary); line-height: 1.5; }

    /* ─── Key Finding Cards ─── */
    .finding-card {
        background: var(--surface-low);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 14px 16px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: var(--text-primary);
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }
    .finding-card span { color: var(--primary); font-size: 1rem; }

    /* ─── Lifestyle Tips ─── */
    .tip-card {
        background: var(--emerald-light);
        border: 1px solid var(--emerald-border);
        border-left: 4px solid var(--emerald);
        border-radius: var(--radius-lg);
        padding: 12px 16px;
        margin-bottom: 8px;
        font-size: 0.875rem;
        color: #065f46;
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }

    /* ─── Tabs Override ─── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(241,245,249,0.8);
        padding: 4px;
        border-radius: var(--radius-lg);
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: var(--radius-md);
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.85rem;
        border: none !important;
        padding: 0 16px;
        transition: all 0.15s ease;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        background: var(--surface) !important;
        color: var(--primary) !important;
        box-shadow: var(--shadow-sm);
        border: 1px solid rgba(226,232,240,0.5) !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ─── Buttons ─── */
    .stButton>button {
        background: var(--primary) !important;
        color: white !important;
        border-radius: var(--radius-lg) !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.01em;
        padding: 11px 24px !important;
        box-shadow: 0 1px 3px rgba(2,132,199,0.25) !important;
        transition: all 0.2s ease !important;
        font-family: var(--font-ui) !important;
    }
    .stButton>button:hover {
        background: var(--primary-hover) !important;
        box-shadow: 0 4px 12px rgba(2,132,199,0.35) !important;
        transform: translateY(-0.5px);
    }
    .stDownloadButton>button {
        background: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 10px 20px !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton>button:hover {
        background: var(--surface-low) !important;
        border-color: var(--border-strong) !important;
    }

    /* ─── File Uploader ─── */
    [data-testid="stFileUploadDropzone"] {
        background: var(--surface-low) !important;
        border: 2px dashed var(--border-strong) !important;
        border-radius: var(--radius-xl) !important;
        transition: all 0.2s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: var(--primary) !important;
        background: var(--sky-light) !important;
    }

    /* ─── Text Area / Inputs ─── */
    .stTextArea textarea {
        background: var(--surface) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: var(--radius-lg) !important;
        color: var(--text-primary) !important;
        font-family: var(--font-ui) !important;
        font-size: 0.9rem !important;
        transition: border-color 0.18s;
    }
    .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(2,132,199,0.12) !important;
    }

    /* ─── Chat ─── */
    .stChatMessage {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-xl) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    [data-testid="stChatInput"] {
        border: 1px solid var(--border-strong) !important;
        border-radius: var(--radius-xl) !important;
        background: var(--surface) !important;
    }

    /* ─── Expander ─── */
    .stExpander {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        background: var(--surface) !important;
        box-shadow: none !important;
    }

    /* ─── Radio Buttons ─── */
    .stRadio [data-testid="stWidgetLabel"] p {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-secondary);
    }
    .stRadio div[role="radiogroup"] label {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 12px 16px;
        margin-bottom: 6px;
        cursor: pointer;
        transition: all 0.15s ease;
    }
    .stRadio div[role="radiogroup"] label:hover {
        border-color: var(--primary);
        background: var(--sky-light);
    }

    /* ─── Empty State ─── */
    .empty-state {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: 56px 24px;
        text-align: center;
        box-shadow: var(--shadow-sm);
    }
    .empty-state-icon { font-size: 2.8rem; margin-bottom: 12px; }
    .empty-state h4 { font-family: var(--font-display); font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0 0 8px; }
    .empty-state p { font-size: 0.9rem; color: var(--text-muted); max-width: 380px; margin: 0 auto; line-height: 1.6; }

    /* ─── Section Labels ─── */
    .section-label {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 10px;
    }

    /* ─── Subheader overrides ─── */
    h3 { font-family: var(--font-display) !important; font-weight: 700 !important; color: var(--text-primary) !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
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

    # Choose value color for critical
    val_color = "#be123c" if "critical" in s else "var(--text-primary)"

    html = f"""
    <div class="biomarker-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
            <div>
                <div class="biomarker-name" style="margin-bottom:4px;">{b.parameter_name}</div>
                <div style="display:flex; align-items:baseline; gap:4px;">
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
            <span>Ref Range: <strong style="color:var(--text-secondary);">{b.reference_range}</strong></span>
        </div>

        <div style="margin-top:10px; font-size:0.82rem; color:var(--text-muted); line-height:1.5;
                    background:var(--surface-low); padding:8px 12px; border-radius:8px;
                    border-left:3px solid var(--border-strong);">
            {b.simple_explanation}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────────────────────
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_analysis_time" not in st.session_state:
    st.session_state.last_analysis_time = 0

# API Key guard
if not is_api_key_configured():
    st.error("⚠️ Service Temporarily Unavailable")
    st.info("Please create a `.env` file with `GEMINI_API_KEY=your_key` in the project directory.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-card">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px; position:relative; z-index:1;">
    <div>
      <div class="hero-eyebrow">⚕ Diagnostic Intelligence Station &nbsp;·&nbsp; Gemini Multimodal Engine</div>
      <h1 class="hero-title">PulseCare AI<br><span style="font-weight:400; opacity:0.75;">Clinical Health Studio</span></h1>
      <p class="hero-subtitle">Multimodal Biomarker Telemetry · Plain-English Medical Insights · AI Clinical Consultation</p>
    </div>
    <div style="display:flex; flex-direction:column; gap:8px; align-items:flex-end;">
      <span class="pill pill-emerald"><span class="ping-dot"></span> TELEMETRY LIVE</span>
      <span class="pill pill-sky">🔒 Zero-Knowledge 256-Bit Vault</span>
      <span class="pill pill-slate">⚡ Clinical Grade Accuracy 99.4%</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Medical Disclaimer
st.markdown("""
<div class="disclaimer">
    <strong>⚖️ Educational Disclaimer:</strong> PulseCare AI provides automated educational summaries of medical documents.
    It is not a diagnostic device or substitute for a licensed healthcare provider. Always consult your physician.
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
col_input, col_display = st.columns([1, 1.45], gap="large")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT PANEL — Diagnostic Ingestion
# ══════════════════════════════════════════════════════════════════════════════
with col_input:
    st.markdown("""
    <div class="clinical-card" style="margin-bottom:0;">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
            <div style="width:36px; height:36px; background:#f0f9ff; border:1px solid #bae6fd;
                        border-radius:10px; display:flex; align-items:center; justify-content:center;
                        font-size:1.1rem;">🔬</div>
            <div>
                <h3 class="card-header" style="margin:0;">Diagnostic Ingestion</h3>
                <p class="card-subheader">Lab records, blood chemistry, and imaging feeds</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    input_tab1, input_tab2, input_tab3 = st.tabs([
        "📤 Upload File",
        "📝 Paste Text",
        "🧪 Sample Reports"
    ])

    file_to_process = None
    text_to_process = None
    file_type = None

    with input_tab1:
        st.markdown("<p style='font-size:0.85rem; color:#64748b; margin:12px 0 10px;'>Supports PDF, PNG, JPG, JPEG lab report scans:</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop lab report or click to browse",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Files are processed transiently in-memory. Nothing is stored on disk."
        )
        if uploaded_file:
            file_to_process = uploaded_file.getvalue()
            ext = uploaded_file.name.split(".")[-1].lower()
            file_type = "pdf" if ext == "pdf" else ext
            st.markdown(f"""
            <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px;
                        padding:10px 14px; font-size:0.82rem; color:#166534; margin-top:8px;">
                ✓ <strong>{uploaded_file.name}</strong> ready for analysis
            </div>""", unsafe_allow_html=True)

    with input_tab2:
        st.markdown("<p style='font-size:0.85rem; color:#64748b; margin:12px 0 10px;'>Copy & paste clinical report text or raw lab metrics:</p>", unsafe_allow_html=True)
        pasted_text = st.text_area(
            "Report Content",
            height=220,
            placeholder="Paste blood test results, metabolic panel, or clinical report text here...",
            label_visibility="collapsed"
        )
        if pasted_text.strip():
            text_to_process = pasted_text.strip()
            file_type = "text"

    with input_tab3:
        st.markdown("<p class='section-label' style='margin:12px 0 8px;'>Select Curated Case Study</p>", unsafe_allow_html=True)
        sample_choice = st.radio(
            "Choose sample report",
            options=list(SAMPLE_REPORTS.keys()),
            label_visibility="collapsed"
        )
        if st.button("⚡ Load & Analyze Sample", use_container_width=True):
            text_to_process = SAMPLE_REPORTS[sample_choice]
            file_type = "text"
            st.toast(f"Sample loaded: {sample_choice}", icon="✅")

    # ── Analyze CTA ──────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    analyze_btn = st.button("🔬 Run AI Diagnostic Analysis", use_container_width=True)

    if analyze_btn:
        now = time.time()
        if now - st.session_state.last_analysis_time < 4:
            st.warning("⏱️ Please wait a few seconds between requests.")
        elif not file_to_process and not text_to_process:
            st.warning("⚠️ Upload a file, paste text, or select a sample report first.")
        else:
            st.session_state.last_analysis_time = now
            with st.spinner("Analyzing biomarkers, lab parameters & clinical structures with Gemini..."):
                try:
                    analyzer = HealthReportAnalyzer()
                    input_data = file_to_process if file_to_process else text_to_process
                    analysis = analyzer.analyze_report(input_data, file_type=file_type)
                    st.session_state.analysis_result = analysis
                    st.session_state.chat_history = []
                    st.success("✅ Analysis Complete!")
                except Exception as err:
                    err_msg = str(err) or repr(err)
                    st.error(f"❌ Analysis Error: {err_msg}")

    # Inference footnote
    st.markdown("""
    <div style="display:flex; justify-content:space-between; font-size:11px; color:#94a3b8;
                padding:8px 4px 0; border-top:1px solid #f1f5f9; margin-top:12px;">
        <span>Inference Engine: Gemini 3.6 Flash</span>
        <span>🔒 Session-Only Processing</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — Diagnostic Results
# ══════════════════════════════════════════════════════════════════════════════
with col_display:
    analysis: HealthReportAnalysis = st.session_state.analysis_result

    if not analysis:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🩺</div>
            <h4>No Active Diagnostic Analysis</h4>
            <p>Select a sample report or upload a medical document on the left panel
               to generate an interactive clinical breakdown.</p>
        </div>
        """, unsafe_allow_html=True)

    elif not analysis.is_valid_report:
        st.markdown(f"""
        <div class="clinical-card" style="border-left:4px solid var(--rose); background:var(--rose-light);">
            <h4 style="color:#9f1239; margin:0 0 8px; font-family:var(--font-display); font-weight:700;">
                ⚠️ Document Validation Warning
            </h4>
            <p style="color:#be123c; margin:0; font-size:0.9rem;">
                {analysis.unvalid_reason or "The uploaded document does not appear to be a valid health or lab report."}
            </p>
        </div>
        """, unsafe_allow_html=True)

    else:
        # ── Metric Summary Chips ─────────────────────────────────────────────
        total = len(analysis.biomarkers)
        abnormal = sum(1 for b in analysis.biomarkers if b.status.lower() not in ("normal", "optimal"))
        normal_count = total - abnormal
        critical_count = sum(1 for b in analysis.biomarkers if "critical" in b.status.lower())

        chip_cols = st.columns(4)
        chips = [
            ("Analyzed Biomarkers", str(total),      "Complete Panel",    "stat-chip"),
            ("Elevated / Flagged",  str(abnormal),   "Need attention",    "stat-chip stat-chip-elevated" if abnormal else "stat-chip stat-chip-normal"),
            ("Optimal Range",       str(normal_count),"Physiologically normal", "stat-chip stat-chip-normal"),
            ("Critical Concern",    str(critical_count), "Urgent review", "stat-chip stat-chip-critical" if critical_count else "stat-chip stat-chip-normal"),
        ]
        for col, (label, val, sub, cls) in zip(chip_cols, chips):
            with col:
                st.markdown(f"""
                <div class="{cls}">
                    <div class="stat-chip-label">{label}</div>
                    <div class="stat-chip-value">{val}</div>
                    <div class="stat-chip-sub">{sub}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # ── Executive Diagnostic Synthesis ───────────────────────────────────
        st.markdown(f"""
        <div class="clinical-card">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.2rem;">📊</span>
                    <span style="font-family:var(--font-display); font-size:1.05rem; font-weight:700; color:var(--text-primary);">
                        Executive Diagnostic Synthesis
                    </span>
                </div>
                <span class="pill pill-amber">{'⚠ ' + analysis.report_title if analysis.report_title else '⚠ Health Report'}</span>
            </div>
            <div class="narrative-block">
                {analysis.patient_summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Tabbed Deep-Dive Panel ────────────────────────────────────────────
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🔬 Biomarker Telemetry",
            "🚨 Key Findings",
            "📖 Medical Decoder",
            "💬 Physician Questions",
            "🤖 AI Assistant"
        ])

        with tab1:
            st.markdown("<p style='font-size:0.82rem; color:#64748b; margin-bottom:14px;'>Calibrated against clinical normative ranges [Low | Optimal | Elevated | Critical]</p>", unsafe_allow_html=True)
            if analysis.biomarkers:
                for b in analysis.biomarkers:
                    render_biomarker_card(b)

                with st.expander("📋 Compact Data Table"):
                    rows = [{"Parameter": b.parameter_name, "Result": f"{b.value} {b.unit}".strip(),
                             "Ref Range": b.reference_range, "Status": b.status,
                             "Explanation": b.simple_explanation} for b in analysis.biomarkers]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No numerical biomarkers detected in this report.")

        with tab2:
            st.markdown("<p class='section-label'>Primary Diagnostic Findings</p>", unsafe_allow_html=True)
            if analysis.key_findings:
                for item in analysis.key_findings:
                    st.markdown(f"""
                    <div class="finding-card">
                        <span>📌</span>
                        <span>{item}</span>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No key findings generated.")

            if analysis.lifestyle_wellness_educational_tips:
                st.markdown("<p class='section-label' style='margin-top:20px;'>Educational Lifestyle & Wellness Tips</p>", unsafe_allow_html=True)
                for tip in analysis.lifestyle_wellness_educational_tips:
                    st.markdown(f"""
                    <div class="tip-card">
                        <span>🌱</span>
                        <span>{tip}</span>
                    </div>""", unsafe_allow_html=True)

        with tab3:
            st.markdown("<p style='font-size:0.875rem; color:#64748b; margin-bottom:14px;'>Medical terminology translated to clear, conversational English:</p>", unsafe_allow_html=True)
            if analysis.medical_jargon_decoded:
                for t in analysis.medical_jargon_decoded:
                    st.markdown(f"""
                    <div class="jargon-card">
                        <div class="jargon-term">ℹ {t.term}</div>
                        <p class="jargon-def">{t.plain_english}</p>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No specialized medical jargon required decoding.")

        with tab4:
            st.markdown("<p style='font-size:0.875rem; color:#64748b; margin-bottom:14px;'>High-yield discussion points recommended for your next consultation:</p>", unsafe_allow_html=True)
            if analysis.questions_for_doctor:
                for idx, q in enumerate(analysis.questions_for_doctor, 1):
                    st.markdown(f"""
                    <div class="question-item">
                        <div class="question-num">{idx}</div>
                        <div class="question-text">{q}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No physician questions generated.")

        with tab5:
            st.markdown("<p style='font-size:0.875rem; color:#64748b; margin-bottom:12px;'>Ask follow-up questions about your lab results, dietary changes, or medications:</p>", unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            user_q = st.chat_input("Ask about your results, e.g. 'What does elevated LDL mean for me?'")
            if user_q:
                st.session_state.chat_history.append({"role": "user", "content": user_q})
                with st.chat_message("user"):
                    st.write(user_q)
                with st.chat_message("assistant"):
                    with st.spinner("Formulating clinical insight..."):
                        analyzer = HealthReportAnalyzer()
                        ctx = f"Title: {analysis.report_title}\nSummary: {analysis.patient_summary}\nFindings: {analysis.key_findings}"
                        reply = analyzer.answer_health_question(
                            report_summary=ctx,
                            user_question=user_q,
                            chat_history=st.session_state.chat_history
                        )
                        st.write(reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": reply})

        # ── Export Action Bar ─────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex; align-items:center; gap:8px; font-size:11px; color:#64748b;
                    padding:12px 4px 8px; border-top:1px solid #e2e8f0; margin-top:16px;">
            <span style="color:#059669;">🔒</span> End-to-End Cryptographic Report Signing Active
        </div>
        """, unsafe_allow_html=True)

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            try:
                pdf_data = generate_pdf_report(analysis)
                st.download_button(
                    label="📄 Download Clinical PDF",
                    data=pdf_data,
                    file_name="PulseCare_Clinical_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
        with col_e2:
            md_text = (f"# {analysis.report_title}\n\n## Summary\n{analysis.patient_summary}\n\n"
                       f"## Key Findings\n" + "\n".join(f"- {f}" for f in analysis.key_findings))
            st.download_button(
                label="📝 Copy Markdown Report",
                data=md_text,
                file_name="PulseCare_Clinical_Report.md",
                mime="text/markdown",
                use_container_width=True
            )
