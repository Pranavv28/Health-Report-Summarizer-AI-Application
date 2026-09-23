import time
import json
import streamlit as st
import pandas as pd

from config import get_active_provider, SAMPLE_REPORTS
from schema import HealthReportAnalysis, Biomarker
from medical_summarizer import MedicalSummarizer
from exporter import generate_pdf_report
import auth as _auth

# Initialise the SQLite database (idempotent)
_auth.init_db()

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
        --jotform-navy:       #064e3b;
        --jotform-dark:       #047857;
        --jotform-orange:     #059669;
        --jotform-blue:       #059669;
        --jotform-blue-light: #f0fdf4;
        --jotform-teal:       #10b981;
        --jotform-teal-light: #ecfdf5;
        --bg-main:            #f4f9f5;
        --surface:            #ffffff;
        --surface-low:        #f8faf7;
        --border-light:       #d1fae5;
        --border-strong:      #059669;
        --text-dark:          #0f291e;
        --text-muted:         #065f46;
        --emerald-badge:      #059669;
        --amber-badge:        #d97706;
        --rose-badge:         #e11d48;
        --shadow-sm:          0 2px 8px rgba(5,150,105,0.06);
        --shadow-md:          0 8px 24px -4px rgba(5,150,105,0.10);
        --shadow-lg:          0 16px 36px -8px rgba(5,150,105,0.14);
        --radius-sm:          8px;
        --radius-md:          12px;
        --radius-lg:          16px;
        --radius-xl:          20px;
        --font-body:          'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-display:       'Outfit', 'Inter', sans-serif;
    }

    /* ─── Global Reset & Clean Streamlit Overrides ─── */
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: var(--font-body);
        color: var(--text-dark);
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-display) !important;
        letter-spacing: -0.02em;
    }

    button, .stButton>button, .stDownloadButton>button {
        font-family: var(--font-display) !important;
    }

    input, textarea, select {
        font-family: var(--font-body) !important;
    }

    .stApp {
        background-color: var(--bg-main) !important;
    }

    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 1400px; }

    /* ─── Top Navigation Header Bar (Clean Green Theme) ─── */
    .jotform-nav {
        background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
        border-radius: var(--radius-lg);
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 20px rgba(6, 78, 59, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .jotform-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .jotform-logo-icon {
        width: 44px; height: 44px;
        background: #ffffff;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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
        background: #10b981;
        color: #064e3b;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.08em;
        padding: 3px 10px;
        border-radius: 999px;
        text-transform: uppercase;
    }
    .jotform-brand-subtitle {
        font-size: 0.82rem;
        color: #a7f3d0;
        margin: 2px 0 0 0;
        font-weight: 500;
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
        font-weight: 700;
        background: rgba(255, 255, 255, 0.15);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(4px);
    }
    .jf-badge-active {
        background: #ffffff;
        color: #064e3b;
        font-weight: 800;
        border-color: #ffffff;
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

    /* ─── Clean Agent Greeting & Hero Card ─── */
    .agent-hero-card {
        background: #ffffff;
        border: 1.5px solid #d1fae5;
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
        background: linear-gradient(90deg, #10b981 0%, #059669 50%, #047857 100%);
    }

    .agent-profile {
        display: flex;
        align-items: flex-start;
        gap: 18px;
    }
    .agent-avatar {
        width: 56px; height: 56px;
        border-radius: 16px;
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        box-shadow: 0 6px 16px rgba(5, 150, 105, 0.3);
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
        font-weight: 800;
        color: #064e3b;
        margin: 0 0 2px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .agent-meta-role {
        font-size: 0.85rem;
        color: #065f46;
        font-weight: 600;
        margin-bottom: 12px;
    }

    .agent-speech-bubble {
        background: #f0fdf4;
        border: 1.5px solid #a7f3d0;
        border-radius: 14px;
        padding: 14px 18px;
        font-size: 0.95rem;
        color: #064e3b;
        line-height: 1.6;
        font-weight: 600;
        position: relative;
    }

    /* ─── Jotform Card Containers ─── */
    .jotform-card {
        background: #ffffff;
        border: 1.5px solid #d1fae5;
        border-radius: var(--radius-xl);
        padding: 24px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 20px;
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .jotform-card:hover {
        box-shadow: var(--shadow-md);
        border-color: #059669;
    }
    .card-title-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1.5px solid #d1fae5;
    }
    .card-title-text {
        font-family: var(--font-display);
        font-size: 1.15rem;
        font-weight: 800;
        color: #064e3b;
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0;
    }

    /* ─── Stat Metric Chips ─── */
    .stat-box {
        background: #f8faf7;
        border: 1.5px solid #d1fae5;
        border-radius: var(--radius-md);
        padding: 16px;
        text-align: left;
    }
    .stat-label {
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #065f46 !important;
        margin-bottom: 4px;
    }
    .stat-value {
        font-family: var(--font-display);
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f291e;
        line-height: 1;
    }
    .stat-subtext {
        font-size: 0.78rem;
        color: #065f46 !important;
        font-weight: 700 !important;
        margin-top: 4px;
    }
    .stat-box-elevated { background: #fffbeb; border-color: #fde68a; }
    .stat-box-elevated .stat-label { color: #92400e !important; }
    .stat-box-elevated .stat-value { color: #b45309 !important; }
    .stat-box-normal { background: #ecfdf5; border-color: #a7f3d0; }
    .stat-box-normal .stat-label { color: #065f46 !important; }
    .stat-box-normal .stat-value { color: #047857 !important; }
    .stat-box-critical { background: #fff1f2; border-color: #fecdd3; }
    .stat-box-critical .stat-label { color: #9f1239 !important; }
    .stat-box-critical .stat-value { color: #be123c !important; }

    /* ─── Executive Narrative Summary ─── */
    .executive-narrative {
        background: #f0fdf4;
        border: 1.5px solid #a7f3d0;
        border-left: 5px solid #059669;
        border-radius: var(--radius-md);
        padding: 18px 20px;
        font-size: 0.96rem;
        color: #0f291e;
        font-weight: 600;
        line-height: 1.65;
    }

    /* ─── Biomarker Card ─── */
    .biomarker-card {
        background: #ffffff;
        border: 1.5px solid #d1fae5;
        border-radius: var(--radius-md);
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    .biomarker-card:hover {
        border-color: #059669;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.12);
    }
    .biomarker-name {
        font-size: 0.95rem;
        font-weight: 800;
        color: #064e3b;
    }
    .biomarker-value {
        font-family: var(--font-display);
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1;
    }
    .biomarker-unit {
        font-size: 0.82rem;
        color: #0f291e !important;
        font-weight: 700 !important;
        margin-left: 4px;
    }

    /* Status Badges */
    .badge-normal   { display:inline-flex; align-items:center; gap:4px; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:800; background:#ecfdf5; color:#047857; border:1.5px solid #a7f3d0; }
    .badge-elevated { display:inline-flex; align-items:center; gap:4px; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:800; background:#fffbeb; color:#b45309; border:1.5px solid #fde68a; }
    .badge-low      { display:inline-flex; align-items:center; gap:4px; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:800; background:#f0f9ff; color:#0369a1; border:1.5px solid #bae6fd; }
    .badge-critical { display:inline-flex; align-items:center; gap:4px; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:800; background:#fff1f2; color:#be123c; border:1.5px solid #fecdd3; }

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
        border: 2.5px solid #064e3b;
        box-shadow: 0 2px 5px rgba(0,0,0,0.25);
        transform: translateX(-50%);
    }
    .gauge-labels {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: #0f291e !important;
        font-weight: 700 !important;
        margin-top: 4px;
    }

    /* ─── Jargon Decoder & Doctor Questions Cards ─── */
    .jargon-box {
        background: #f0fdf4;
        border: 1.5px solid #a7f3d0;
        border-radius: var(--radius-md);
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .jargon-term {
        font-size: 0.95rem;
        font-weight: 800;
        color: #059669;
        margin-bottom: 4px;
    }
    .jargon-def { font-size: 0.9rem; color: #0f291e !important; font-weight: 600; margin: 0; line-height: 1.5; }

    .doc-question-card {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        background: #ffffff;
        border: 1.5px solid #d1fae5;
        border-radius: var(--radius-md);
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .doc-question-num {
        width: 26px; height: 26px;
        border-radius: 50%;
        background: #ecfdf5;
        color: #059669;
        border: 1.5px solid #a7f3d0;
        font-weight: 800;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    /* ─── Streamlit Tabs Container & Tab List ─── */
    div[data-baseweb="tab-list"],
    [data-testid="stTabList"],
    [role="tablist"] {
        gap: 8px !important;
        background: #e6f4ea !important;
        padding: 6px !important;
        border-radius: 12px !important;
        border: 1.5px solid #a7f3d0 !important;
        margin-bottom: 16px !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
    }

    /* Tab Button (Base / Inactive) */
    button[data-baseweb="tab"],
    [data-testid="stTab"],
    div[data-baseweb="tab-list"] button[role="tab"],
    [role="tablist"] button[role="tab"] {
        height: 42px !important;
        min-height: 42px !important;
        border-radius: 10px !important;
        padding: 6px 18px !important;
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1.5px solid #a7f3d0 !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
        transition: all 0.15s ease !important;
        cursor: pointer !important;
    }

    /* Tab Button Text & Icons (Inactive) */
    button[data-baseweb="tab"] p,
    button[data-baseweb="tab"] span,
    button[data-baseweb="tab"] div,
    [data-testid="stTab"] p,
    [data-testid="stTab"] span,
    [data-testid="stTab"] div,
    div[data-baseweb="tab-list"] button[role="tab"] p,
    div[data-baseweb="tab-list"] button[role="tab"] span,
    div[data-baseweb="tab-list"] button[role="tab"] div,
    [role="tablist"] button[role="tab"] p,
    [role="tablist"] button[role="tab"] span,
    [role="tablist"] button[role="tab"] div {
        color: #064e3b !important;
        -webkit-text-fill-color: #064e3b !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        opacity: 1 !important;
        pointer-events: none !important;
    }

    /* Tab Hover */
    button[data-baseweb="tab"]:hover,
    [data-testid="stTab"]:hover,
    div[data-baseweb="tab-list"] button[role="tab"]:hover,
    [role="tablist"] button[role="tab"]:hover {
        background-color: #f0fdf4 !important;
        background: #f0fdf4 !important;
        border-color: #059669 !important;
    }

    /* Tab Button (Active / Selected) */
    button[data-baseweb="tab"][aria-selected="true"],
    [data-testid="stTab"][aria-selected="true"],
    div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"],
    [role="tablist"] button[role="tab"][aria-selected="true"] {
        background-color: #047857 !important;
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        border-color: #047857 !important;
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35) !important;
    }

    /* Tab Button Text & Icons (Active / Selected) */
    button[data-baseweb="tab"][aria-selected="true"] p,
    button[data-baseweb="tab"][aria-selected="true"] span,
    button[data-baseweb="tab"][aria-selected="true"] div,
    [data-testid="stTab"][aria-selected="true"] p,
    [data-testid="stTab"][aria-selected="true"] span,
    [data-testid="stTab"][aria-selected="true"] div,
    div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] p,
    div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] span,
    div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] div,
    [role="tablist"] button[role="tab"][aria-selected="true"] p,
    [role="tablist"] button[role="tab"][aria-selected="true"] span,
    [role="tablist"] button[role="tab"][aria-selected="true"] div {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        opacity: 1 !important;
        pointer-events: none !important;
    }

    /* Tab Panel Content Container */
    div[data-baseweb="tab-panel"],
    div[role="tabpanel"],
    [data-testid="stTabContent"] {
        width: 100% !important;
        padding-top: 8px !important;
        display: block !important;
    }

    /* Hide default indicator underline bar */
    [data-baseweb="tab-border"],
    div[data-baseweb="tab-highlight"],
    [data-testid="stTabHighlight"] {
        display: none !important;
    }

    /* ─── Radio Button High-Contrast Fix ─── */
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label p,
    [data-testid="stRadio"] label span,
    [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
        color: #0f291e !important;
        font-size: 0.92rem !important;
        font-weight: 700 !important;
    }
    /* Selected radio dot colour */
    [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
        border-color: #059669 !important;
        background: #059669 !important;
    }
    /* Summary mode radio row — compact pill style */
    .summary-mode-row [data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row;
        gap: 10px;
        flex-wrap: wrap;
    }
    .summary-mode-row [data-testid="stRadio"] label {
        background: #ffffff !important;
        border: 2px solid #a7f3d0 !important;
        border-radius: 12px !important;
        padding: 8px 18px !important;
        cursor: pointer;
        transition: all 0.15s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .summary-mode-row [data-testid="stRadio"] label:hover {
        border-color: #059669 !important;
        background: #f0fdf4 !important;
    }

    /* Action Buttons (Emerald Green Palette) */
    .stButton>button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        color: #ffffff !important;
        border-radius: var(--radius-md) !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(5, 150, 105, 0.45) !important;
    }
    /* Primary button extra pop */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        box-shadow: 0 4px 16px rgba(5, 150, 105, 0.4) !important;
        font-size: 1.05rem !important;
        padding: 14px 24px !important;
    }
    .stButton>button[kind="primary"]:hover {
        box-shadow: 0 6px 22px rgba(5, 150, 105, 0.55) !important;
    }

    .stDownloadButton>button {
        background: #ffffff !important;
        color: #059669 !important;
        border: 2px solid #059669 !important;
        border-radius: var(--radius-md) !important;
        font-weight: 800 !important;
        font-size: 0.9rem !important;
        padding: 10px 20px !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton>button:hover {
        background: #f0fdf4 !important;
        border-color: #047857 !important;
        color: #047857 !important;
    }

    [data-testid="stFileUploadDropzone"] {
        background: #f8faf7 !important;
        border: 2px dashed #a7f3d0 !important;
        border-radius: var(--radius-lg) !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #059669 !important;
        background: #f0fdf4 !important;
    }

    /* ─── Left Intake Panel: Robust Sticky Sidebar ─── */
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > div:first-child,
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > [data-testid="column"]:first-child {
        position: sticky !important;
        top: 1rem !important;
        align-self: flex-start !important;
        max-height: calc(100vh - 2rem) !important;
        overflow-y: auto !important;
        padding-right: 6px !important;
    }

    /* Custom subtle thin scrollbar for sticky left intake panel */
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > div:first-child::-webkit-scrollbar,
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > [data-testid="column"]:first-child::-webkit-scrollbar {
        width: 5px;
    }
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > div:first-child::-webkit-scrollbar-track,
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > [data-testid="column"]:first-child::-webkit-scrollbar-track {
        background: transparent;
    }
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > div:first-child::-webkit-scrollbar-thumb,
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > [data-testid="column"]:first-child::-webkit-scrollbar-thumb {
        background: #a7f3d0;
        border-radius: 999px;
    }
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > div:first-child::-webkit-scrollbar-thumb:hover,
    [data-testid="stHorizontalBlock"]:has(.intake-panel-anchor) > [data-testid="column"]:first-child::-webkit-scrollbar-thumb:hover {
        background: #059669;
    }

    /* ─── Streamlit Form & Text Input High-Quality Polish ─── */
    div[data-testid="stForm"] {
        background: #ffffff !important;
        border: 1.5px solid #d1fae5 !important;
        border-radius: 18px !important;
        padding: 24px 28px !important;
        box-shadow: 0 8px 28px rgba(5, 150, 105, 0.08) !important;
    }
    div[data-testid="stTextInput"] > div > div {
        background: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stTextInput"] input {
        color: #0f291e !important;
        font-family: var(--font-body) !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stTextInput"] > div > div:focus-within {
        border-color: #059669 !important;
        box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.2) !important;
    }
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        font-family: var(--font-body) !important;
        font-weight: 600 !important;
    }

    /* ─── Empty State Placeholder ─── */
    .empty-agent-state {
        background: #ffffff;
        border: 2px dashed #a7f3d0;
        border-radius: var(--radius-xl);
        padding: 60px 24px;
        text-align: center;
        color: #065f46;
    }
    .empty-agent-icon {
        font-size: 3rem;
        margin-bottom: 12px;
    }

    /* ─── Streamlit Header Status Widget & 'Source file changed' Toolbar ─── */
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    [data-testid="stAppToolbar"],
    div[class*="stStatusWidget"] {
        color: #0f172a !important;
        background-color: #ffffff !important;
        border: 2px solid #059669 !important;
        border-radius: 12px !important;
        padding: 8px 16px !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
        z-index: 999999 !important;
    }
    [data-testid="stStatusWidget"] p,
    [data-testid="stStatusWidget"] span,
    [data-testid="stStatusWidget"] div,
    [data-testid="stToolbar"] p,
    [data-testid="stToolbar"] span,
    [data-testid="stToolbar"] div {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
    }

    /* Buttons inside the "Source file changed" widget ("Always rerun", "Rerun") */
    [data-testid="stStatusWidget"] button,
    [data-testid="stToolbar"] button,
    header[data-testid="stHeader"] button {
        background: #059669 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: 1px solid #047857 !important;
        border-radius: 8px !important;
        padding: 5px 14px !important;
        font-weight: 800 !important;
        font-size: 0.88rem !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 2px 6px rgba(5, 150, 105, 0.3) !important;
    }
    [data-testid="stStatusWidget"] button:hover,
    [data-testid="stToolbar"] button:hover,
    header[data-testid="stHeader"] button:hover {
        background: #047857 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    [data-testid="stStatusWidget"] button *,
    [data-testid="stToolbar"] button *,
    header[data-testid="stHeader"] button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 800 !important;
    }

    /* ─── High Contrast Spinner ─── */
    [data-testid="stSpinner"],
    .stSpinner {
        color: #064e3b !important;
        background-color: #f0fdf4 !important;
        border: 1.5px solid #a7f3d0 !important;
        border-radius: 12px !important;
        padding: 12px 18px !important;
        margin: 12px 0 !important;
        box-shadow: 0 4px 12px rgba(5,150,105,0.08) !important;
    }
    [data-testid="stSpinner"] p,
    [data-testid="stSpinner"] span,
    [data-testid="stSpinner"] div,
    .stSpinner p,
    .stSpinner span,
    .stSpinner div {
        color: #064e3b !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }

    /* ─── Chat Message High Contrast & Font Size Fix ─── */
    [data-testid="stChatMessage"] {
        background-color: #ffffff !important;
        border: 1.5px solid #d1fae5 !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 2px 6px rgba(5,150,105,0.04) !important;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessageContent"] {
        color: #0f291e !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        line-height: 1.6 !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: #f0fdf4 !important;
        border-color: #a7f3d0 !important;
    }

    /* ─── Universal Responsive Device Format Compatibility & Media Queries ─── */
    *, ::before, ::after {
        box-sizing: border-box !important;
    }
    
    .stApp, .block-container, .jotform-card, .agent-hero-card, .biomarker-card, .stat-box {
        word-break: break-word;
        overflow-wrap: break-word;
    }

    /* Horizontal scroll for table elements on touch screens */
    .stTable, [data-testid="stTable"], .element-container iframe, table {
        max-width: 100% !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }

    /* BaseWeb Tabs horizontal touch scrolling on mobile devices */
    @media (max-width: 768px) {
        div[data-testid="stTabList"],
        div[data-baseweb="tab-list"],
        [role="tablist"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch !important;
            width: 100% !important;
            max-width: 100% !important;
            white-space: nowrap !important;
        }
        button[data-baseweb="tab"],
        [data-testid="stTab"],
        div[data-baseweb="tab-list"] button[role="tab"],
        [role="tablist"] button[role="tab"] {
            flex: 0 0 auto !important;
            padding: 0 12px !important;
            font-size: 0.85rem !important;
        }
    }

    /* Tablet & Smartphone (<= 992px) Layout Fixes */
    @media (max-width: 992px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 0.5rem !important;
        }

        /* Disable fixed sticky sidebar height clipping on tablets and smartphones */
        [data-testid="stHorizontalBlock"] > div:first-child,
        [data-testid="column"]:first-child,
        div[data-testid="stColumn"]:first-child {
            position: static !important;
            max-height: none !important;
            overflow-y: visible !important;
            width: 100% !important;
            margin-bottom: 20px !important;
        }

        .jotform-nav {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 12px !important;
            padding: 16px !important;
        }
        .jotform-status-badges {
            flex-wrap: wrap !important;
            width: 100% !important;
        }

        .agent-profile {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 12px !important;
        }
        .agent-avatar {
            width: 44px !important;
            height: 44px !important;
            font-size: 1.4rem !important;
        }
    }

    /* Mobile Phone Devices (<= 576px) Fine-tuning */
    @media (max-width: 576px) {
        .jotform-brand-title {
            font-size: 1.1rem !important;
        }
        .jotform-brand-subtitle {
            font-size: 0.75rem !important;
        }
        .stat-value {
            font-size: 1.4rem !important;
        }
        .biomarker-value {
            font-size: 1.2rem !important;
        }
        .agent-hero-card, .jotform-card {
            padding: 16px !important;
            border-radius: var(--radius-lg) !important;
        }
        .stButton > button, .stDownloadButton > button {
            width: 100% !important;
            min-height: 44px !important;
        }
    }

    /* ─── Auth Page Styles ─── */
    .auth-card-header {
        text-align: center;
        padding: 24px 16px 14px;
        margin-bottom: 8px;
    }
    .auth-logo-icon {
        font-size: 2.6rem;
        display: inline-block;
        background: linear-gradient(135deg, #059669, #047857);
        border-radius: 18px;
        width: 66px; height: 66px;
        line-height: 66px;
        text-align: center;
        box-shadow: 0 8px 22px rgba(5,150,105,0.32);
        margin-bottom: 14px;
    }
    .auth-title {
        font-family: var(--font-display);
        font-size: 1.85rem;
        font-weight: 800;
        color: #064e3b;
        letter-spacing: -0.025em;
        margin: 0 0 6px;
        text-align: center;
    }
    .auth-subtitle {
        font-size: 0.92rem;
        color: #065f46;
        font-weight: 600;
        text-align: center;
        margin: 0;
    }
    /* Logged-in user badge in nav */
    .user-badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255,255,255,0.18);
        border: 1.5px solid rgba(255,255,255,0.30);
        border-radius: 999px;
        padding: 6px 16px;
        font-size: 0.82rem;
        font-weight: 700;
        color: #ffffff;
        backdrop-filter: blur(4px);
    }
    .user-badge-avatar {
        width: 24px; height: 24px;
        border-radius: 50%;
        background: #10b981;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 800;
        color: #ffffff;
        flex-shrink: 0;
    }
    /* History report cards */
    .history-card {
        background: #ffffff;
        border: 1.5px solid #d1fae5;
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    .history-card:hover {
        border-color: #059669;
        box-shadow: 0 4px 12px rgba(5,150,105,0.12);
    }
    .history-card-title {
        font-family: var(--font-display);
        font-size: 0.97rem;
        font-weight: 800;
        color: #064e3b;
        margin-bottom: 4px;
    }
    .history-card-meta {
        font-size: 0.8rem;
        color: #065f46;
        font-weight: 600;
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
            <span>Reference Range: <strong style="color:#0f172a; font-weight:800;">{b.reference_range}</strong></span>
        </div>

        <div style="margin-top:10px; font-size:0.88rem; color:#064e3b; font-weight:600; line-height:1.55;
                    background:#f0fdf4; padding:10px 14px; border-radius:10px;
                    border-left:3.5px solid #059669;">
            💡 <strong>Explanation:</strong> {b.simple_explanation}
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
if "uploaded_file_bytes" not in st.session_state:
    st.session_state.uploaded_file_bytes = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
if "uploaded_file_type" not in st.session_state:
    st.session_state.uploaded_file_type = "pdf"

# ── Auth session keys ──
if "jwt_token" not in st.session_state:
    st.session_state.jwt_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None   # {id, name, email}
if "auth_tab" not in st.session_state:
    st.session_state.auth_tab = "login"    # "login" | "signup"
if "history_loaded" not in st.session_state:
    st.session_state.history_loaded = False


# ─────────────────────────────────────────────────────────────────────────────
# JWT VERIFICATION — restore user from existing token
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.jwt_token and st.session_state.current_user is None:
    payload = _auth.verify_jwt(st.session_state.jwt_token)
    if payload:
        st.session_state.current_user = {
            "id": int(payload["sub"]),
            "name": payload["name"],
            "email": payload["email"],
        }
    else:
        # Token expired / invalid — clear it
        st.session_state.jwt_token = None


# ─────────────────────────────────────────────────────────────────────────────
# AUTH GATE — show Login / Sign Up page if not authenticated
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.current_user is None:

    # Centered authentication column
    _, auth_col, _ = st.columns([1, 1.4, 1])
    with auth_col:
        st_html("""
        <div class="auth-card-header">
            <div class="auth-logo-icon">🩺</div>
            <div class="auth-title">Health Report AI</div>
            <p class="auth-subtitle">Conversational Health Diagnostics &bull; Secure User Portal</p>
        </div>
        """)

        tab_login, tab_signup = st.tabs(["🔑 Sign In", "✨ Create Account"])

        # ── LOGIN ──
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                st.markdown("<p style='font-size:0.88rem;font-weight:700;color:#064e3b;margin:0 0 6px;'>Email Address</p>", unsafe_allow_html=True)
                login_email = st.text_input("Email", placeholder="you@example.com", label_visibility="collapsed", key="li_email")
                st.markdown("<p style='font-size:0.88rem;font-weight:700;color:#064e3b;margin:14px 0 6px;'>Password</p>", unsafe_allow_html=True)
                login_pw = st.text_input("Password", type="password", placeholder="••••••••", label_visibility="collapsed", key="li_pw")
                st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
                login_btn = st.form_submit_button("🔑 Sign In to Portal", use_container_width=True, type="primary")

            if login_btn:
                if not login_email.strip() or not login_pw:
                    st.error("Please enter your email and password.")
                else:
                    user = _auth.authenticate_user(login_email.strip(), login_pw)
                    if user is None:
                        st.error("❌ Invalid email or password. Please try again.")
                    else:
                        token = _auth.create_jwt(user["id"], user["email"], user["name"])
                        st.session_state.jwt_token = token
                        st.session_state.current_user = user
                        st.session_state.history_loaded = False
                        st.success(f"✅ Welcome back, {user['name']}!")
                        st.rerun()

        # ── SIGN UP ──
        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                st.markdown("<p style='font-size:0.88rem;font-weight:700;color:#064e3b;margin:0 0 6px;'>Full Name</p>", unsafe_allow_html=True)
                su_name = st.text_input("Full Name", placeholder="Jane Doe", label_visibility="collapsed", key="su_name")
                st.markdown("<p style='font-size:0.88rem;font-weight:700;color:#064e3b;margin:14px 0 6px;'>Email Address</p>", unsafe_allow_html=True)
                su_email = st.text_input("Email", placeholder="you@example.com", label_visibility="collapsed", key="su_email")
                st.markdown("<p style='font-size:0.88rem;font-weight:700;color:#064e3b;margin:14px 0 6px;'>Password</p>", unsafe_allow_html=True)
                su_pw = st.text_input("Password", type="password", placeholder="Min. 8 characters", label_visibility="collapsed", key="su_pw")
                st.markdown("<p style='font-size:0.88rem;font-weight:700;color:#064e3b;margin:14px 0 6px;'>Confirm Password</p>", unsafe_allow_html=True)
                su_pw2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password", label_visibility="collapsed", key="su_pw2")
                st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
                signup_btn = st.form_submit_button("✨ Create Free Account", use_container_width=True, type="primary")

            if signup_btn:
                errors = []
                if not su_name.strip():
                    errors.append("Name is required.")
                if "@" not in su_email or "." not in su_email:
                    errors.append("Enter a valid email address.")
                if len(su_pw) < 8:
                    errors.append("Password must be at least 8 characters.")
                if su_pw != su_pw2:
                    errors.append("Passwords do not match.")
                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    result = _auth.create_user(su_name.strip(), su_email.strip(), su_pw)
                    if result["ok"]:
                        user = result["user"]
                        token = _auth.create_jwt(user["id"], user["email"], user["name"])
                        st.session_state.jwt_token = token
                        st.session_state.current_user = user
                        st.session_state.history_loaded = False
                        st.success(f"🎉 Account created! Welcome, {user['name']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")

    st.stop()   # Don't render the main app until authenticated


# ── From here on the user is authenticated ──
_current_user: dict = st.session_state.current_user


# Provider detection
active_provider = get_active_provider()
provider_display_name = {
    "groq": "Groq AI (Llama 3.3)",
    "gemini": "Google Gemini 2.0",
    "anthropic": "Claude 3.5 Sonnet",
    "none": "No Provider Configured"
}.get(active_provider, "AI Engine")

if active_provider == "none":
    st.error("⚠️ No AI Provider API Key Found")
    st.markdown("""
    <div style="background:#fff7ed; border:1px solid #fed7aa; border-radius:12px; padding:16px 20px; margin-top:8px;">
        <p style="font-weight:700; color:#c2410c; margin:0 0 10px;">To run this app you need a free Groq API key.</p>
        <p style="color:#7c3aed; margin:0 0 6px;"><strong>On Streamlit Cloud:</strong></p>
        <ol style="color:#374151; font-size:0.9rem; margin:0 0 10px; padding-left:18px;">
            <li>Go to your app dashboard → <strong>Settings → Secrets</strong></li>
            <li>Add this line:<br><code style="background:#f3f4f6; padding:2px 6px; border-radius:4px;">GROQ_API_KEY = "gsk_your_key_here"</code></li>
            <li>Click <strong>Save</strong> — the app will auto-restart</li>
        </ol>
        <p style="color:#374151; font-size:0.85rem; margin:0;">
            Get a free key at <strong>console.groq.com</strong> (no credit card needed)
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TOP JOTFORM NAVIGATION BAR
# ─────────────────────────────────────────────────────────────────────────────
_user_initials = "".join(w[0].upper() for w in _current_user["name"].split()[:2])
st_html(f"""
<div class="jotform-nav">
  <div class="jotform-brand">
    <div class="jotform-logo-icon">🩺</div>
    <div>
      <div class="jotform-brand-title">
        Jotform AI Agents <span class="jotform-brand-tag">MEDICAL AGENT</span>
      </div>
      <p class="jotform-brand-subtitle">Medical Report AI Agent — Conversational Health Diagnostics &amp; Telemetry</p>
    </div>
  </div>
  <div class="jotform-status-badges">
    <span class="jf-badge jf-badge-active"><span class="live-dot"></span> AI Agent Active</span>
    <span class="jf-badge">🔒 HIPAA Compliant</span>
    <span class="jf-badge">⚡ {provider_display_name}</span>
    <span class="user-badge-pill">
      <span class="user-badge-avatar">{_user_initials}</span>
      {_current_user["name"]}
    </span>
  </div>
</div>
""")

# Sign-Out button (right-aligned)
_signout_spacer, _signout_col = st.columns([6, 1])
with _signout_col:
    if st.button("🚪 Sign Out", use_container_width=True, key="signout_btn"):
        st.session_state.jwt_token = None
        st.session_state.current_user = None
        st.session_state.analysis_result = None
        st.session_state.chat_history = []
        st.session_state.history_loaded = False
        st.rerun()


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
    <div class="intake-panel-anchor" style="background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
                border-radius:14px; padding:16px 20px; margin-bottom:16px;
                border:1px solid rgba(255,255,255,0.15); box-shadow: 0 4px 14px rgba(6,78,59,0.25);">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <h3 style="font-family:'Outfit',sans-serif; font-size:1.15rem; font-weight:800;
                       color:#ffffff; margin:0; display:flex; align-items:center; gap:10px;">
                📥 Diagnostic Data Ingestion
            </h3>
            <span style="font-size:11px; font-weight:800; color:#064e3b; background:#ffffff;
                         padding:4px 12px; border-radius:999px; text-transform:uppercase; letter-spacing:0.05em;">Agent Intake Form</span>
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
        st.markdown("<p style='font-size:0.88rem; font-weight:600; color:#1e293b; margin:10px 0 8px;'>Upload scanned blood tests, CBC, or metabolic PDFs/Images:</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop your medical report file here",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            help="Files are processed transiently in-memory and never saved to disk."
        )
        if uploaded_file:
            st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
            st.session_state.uploaded_file_name = uploaded_file.name
            ext = uploaded_file.name.split(".")[-1].lower()
            st.session_state.uploaded_file_type = "pdf" if ext == "pdf" else ("text" if ext == "txt" else ext)
            file_to_process = st.session_state.uploaded_file_bytes
            file_type = st.session_state.uploaded_file_type

            st_html(f"""
            <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:10px; padding:10px 14px; font-size:0.88rem; color:#047857; margin-top:8px; font-weight:600;">
                ✓ <strong>{uploaded_file.name}</strong> uploaded successfully and ready for analysis.
            </div>""")

    with tab_text:
        st.markdown("<p style='font-size:0.88rem; font-weight:600; color:#1e293b; margin:10px 0 8px;'>Paste raw medical report text or lab metrics:</p>", unsafe_allow_html=True)
        pasted_text = st.text_area(
            "Report Content Text",
            height=200,
            value=st.session_state.input_text_val,
            placeholder="Paste lab report details here...",
            label_visibility="collapsed"
        )
        if pasted_text.strip():
            text_to_process = pasted_text.strip()
            st.session_state.input_text_val = text_to_process
            file_type = "text"

    with tab_samples:
        st.markdown("<p style='font-size:0.88rem; font-weight:600; color:#1e293b; margin:10px 0 8px;'>Evaluate using pre-configured clinical case studies:</p>", unsafe_allow_html=True)
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
                st.session_state.input_text_val = text_to_process
                file_type = "text"
                trigger_sample = True

    st_html("""
    <div style='margin:18px 0 8px; padding:10px 14px; background:#f8fafc;
                border:1px solid #cbd5e1; border-radius:10px;'>
        <p style='font-size:0.85rem; font-weight:800; color:#0f172a;
                  text-transform:uppercase; letter-spacing:0.06em; margin:0;'>
            📊 Select Summary Mode
        </p>
    </div>
    """)
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

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    run_agent_btn = st.button("🚀 Analyze Report", use_container_width=True, type="primary")

    # Trigger analysis if button clicked OR 1-Click Analyze Sample clicked
    if run_agent_btn or trigger_sample:
        input_data = None
        # Priority: file uploaded in file_uploader -> session_state uploaded_file -> text_to_process -> session_state input_text_val
        if file_to_process:
            input_data = file_to_process
            file_type = file_type
        elif st.session_state.get("uploaded_file_bytes"):
            input_data = st.session_state.uploaded_file_bytes
            file_type = st.session_state.uploaded_file_type
        elif text_to_process:
            input_data = text_to_process
            file_type = "text"
        elif st.session_state.input_text_val:
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

                        # ── Auto-save to user memory ──
                        try:
                            _auth.save_report(
                                user_id=_current_user["id"],
                                title=analysis.report_title or "Health Report",
                                summary_json=analysis.model_dump_json(),
                                findings_count=len(analysis.biomarkers),
                            )
                            st.session_state.history_loaded = False  # force refresh
                        except Exception as _save_err:
                            pass  # non-blocking — don't fail the analysis

                        st.success(f"✅ {summary_type} Analysis Complete!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"❌ Analysis Failed: {str(err) or repr(err)}")
                        st.info("💡 Tip: Ensure your PDF is not password-protected and contains readable laboratory text or values.")

    st_html(f"""
    <div style="font-size:0.85rem; font-weight:700; color:#334155; background:#ffffff; border:1px solid #cbd5e1; padding:10px 16px; border-radius:12px; text-align:center; margin-top:20px; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
        ⚡ Powered by <strong style="color:#ff6100;">Jotform Agent Builder</strong> & <strong style="color:#0066ff;">{provider_display_name}</strong> Engine
    </div>
    """)


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

        # Quick access to user's saved report memory
        saved_history = _auth.get_report_history(_current_user["id"])
        if saved_history:
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            st_html(f"""
            <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; padding:14px 18px; margin-bottom:14px;">
                <h4 style="font-family:var(--font-display); font-size:1.05rem; font-weight:700; color:#0a1526; margin:0 0 4px; display:flex; align-items:center; gap:8px;">
                    📂 Saved Reports Memory ({len(saved_history)})
                </h4>
                <p style="font-size:0.85rem; color:#475569; margin:0;">
                    Your previously analyzed reports — click <strong>Restore</strong> to view full diagnostics.
                </p>
            </div>
            """)
            for rec in saved_history:
                try:
                    import datetime as _dt
                    dt_obj = _dt.datetime.fromisoformat(rec["created_at"])
                    date_str = dt_obj.strftime("%b %d, %Y — %H:%M UTC")
                except Exception:
                    date_str = rec["created_at"][:16]

                hcol1, hcol2 = st.columns([5, 1])
                with hcol1:
                    st_html(f"""
                    <div class="history-card">
                        <div class="history-card-title">📋 {rec['title']}</div>
                        <div class="history-card-meta">
                            🕐 {date_str} &nbsp;·&nbsp;
                            🔬 {rec['findings_count']} biomarker(s) extracted
                        </div>
                    </div>
                    """)
                    if st.button("📂 Restore", key=f"restore_home_{rec['id']}", use_container_width=True):
                        try:
                            full_rec = _auth.get_report_by_id(rec["id"], _current_user["id"])
                            if full_rec:
                                restored = HealthReportAnalysis.model_validate_json(full_rec["summary_json"])
                                st.session_state.analysis_result = restored
                                st.session_state.chat_history = []
                                st.toast(f"✅ Restored: {rec['title']}", icon="📂")
                                st.rerun()
                        except Exception as _re:
                            st.error(f"Could not restore: {_re}")
                with hcol2:
                    if st.button("🗑️", key=f"del_home_{rec['id']}", help="Delete this report", use_container_width=True):
                        _auth.delete_report(rec["id"], _current_user["id"])
                        st.toast("🗑️ Report deleted.", icon="🗑️")
                        st.rerun()

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
                  <div style="background:#f0fdf4; border:1.5px solid #a7f3d0; border-radius:12px; padding:12px 18px; margin-bottom:16px; font-size:0.9rem; color:#064e3b; font-weight:700; display:flex; gap:18px; flex-wrap:wrap; box-shadow:var(--shadow-sm);">
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
        <div style="background: #ffffff; border: 2px solid #059669; border-radius: var(--radius-xl);
                    padding: 22px 26px; margin-bottom: 22px; box-shadow: var(--shadow-md);">
            <div style="display:flex; align-items:center; justify-content:space-between;
                        margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1.5px solid #d1fae5;">
                <h3 style="font-family:var(--font-display); font-size:1.25rem; font-weight:800;
                           color:#064e3b; margin:0; display:flex; align-items:center; gap:10px;">
                    📋 Executive Diagnostic Synthesis
                </h3>
                <span style="font-size:11px; font-weight:800; color:#064e3b; background:#ecfdf5;
                             border:1px solid #a7f3d0; padding:4px 12px; border-radius:999px; text-transform:uppercase; letter-spacing:0.05em;">Clinical Overview</span>
            </div>
            <div style="font-size:1.02rem; color:#0f291e; line-height:1.75; font-weight:600;">
                {analysis.patient_summary}
            </div>
        </div>
        """)

        # Tabbed Views: Structured Sections
        out_tab1, out_tab2, out_tab3, out_tab4, out_tab5, out_tab6 = st.tabs([
            "⚠️ Abnormal Values",
            "🩺 Key Findings",
            "🔬 Biomarker Telemetry",
            "💊 Treatment & Guidance",
            "🤖 Ask AI Agent",
            "📂 My Reports",
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
                    <div style="background:#f0fdf4; border:1.5px solid #a7f3d0; border-radius:10px; padding:12px 16px; margin-bottom:8px; font-size:0.9rem; color:#064e3b; font-weight:600; display:flex; gap:10px;">
                        <span style="color:#059669;">📌</span> <span>{finding}</span>
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
            st_html("""
            <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; padding:14px 18px; margin-bottom:14px;">
                <h4 style="font-family:var(--font-display); font-size:1.05rem; font-weight:700; color:#0a1526; margin:0 0 4px; display:flex; align-items:center; gap:8px;">
                    🤖 Ask Your Jotform Medical AI Agent
                </h4>
                <p style="font-size:0.85rem; color:#475569; margin:0;">
                    Ask any follow-up question about your lab results, abnormal biomarkers, or doctor consultation.
                </p>
            </div>
            """)

            # 1-Click Suggested Questions
            q1, q2, q3 = st.columns(3)
            suggested_q = None
            with q1:
                if st.button("💡 How to lower high levels?", use_container_width=True):
                    suggested_q = "How can I lower my abnormal biomarker levels through diet and lifestyle?"
            with q2:
                if st.button("🩺 Questions for my doctor?", use_container_width=True):
                    suggested_q = "What key questions should I ask my physician about these report findings?"
            with q3:
                if st.button("💊 Medication considerations?", use_container_width=True):
                    suggested_q = "Are there any specific medications or treatments I should discuss with my doctor?"

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

            # Compact Fixed-Height Scrollable Chat Box
            chat_box = st.container(height=320)
            with chat_box:
                if not st.session_state.chat_history:
                    st_html("""
                    <div style="text-align:center; padding:30px 10px; color:#64748b; font-size:0.88rem;">
                        💬 No messages yet. Select a prompt above or type your question below!
                    </div>
                    """)
                else:
                    for msg in st.session_state.chat_history:
                        with st.chat_message(msg["role"]):
                            st.write(msg["content"])

            user_q = st.chat_input("Ask a follow-up question...") or suggested_q
            if user_q:
                st.session_state.chat_history.append({"role": "user", "content": user_q})
                with st.spinner("Jotform Medical Agent is formulating response..."):
                    summarizer = MedicalSummarizer()
                    ctx = f"Report Title: {analysis.report_title}\nSummary: {analysis.patient_summary}\nFindings: {analysis.key_findings}"
                    reply = summarizer.answer_health_question(
                        report_summary=ctx,
                        user_question=user_q,
                        chat_history=st.session_state.chat_history
                    )
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

        with out_tab6:
            # ── MY REPORTS (memory / history) ──
            st_html("""
            <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; padding:14px 18px; margin-bottom:14px;">
                <h4 style="font-family:var(--font-display); font-size:1.05rem; font-weight:700; color:#0a1526; margin:0 0 4px; display:flex; align-items:center; gap:8px;">
                    📂 My Report History
                </h4>
                <p style="font-size:0.85rem; color:#475569; margin:0;">
                    Your last 50 analyses — click a card to restore that report.
                </p>
            </div>
            """)

            if not st.session_state.history_loaded:
                st.session_state._report_history = _auth.get_report_history(_current_user["id"])
                st.session_state.history_loaded = True

            history_records = st.session_state.get("_report_history", [])

            if st.button("🔄 Refresh History", key="refresh_history"):
                st.session_state._report_history = _auth.get_report_history(_current_user["id"])
                st.session_state.history_loaded = True
                st.rerun()

            if not history_records:
                st_html("""
                <div style="text-align:center; padding:40px 10px; color:#64748b; font-size:0.9rem;">
                    📭 No saved reports yet. Analyze a report to start building your history!
                </div>
                """)
            else:
                for rec in history_records:
                    # Parse date nicely
                    try:
                        import datetime as _dt
                        dt_obj = _dt.datetime.fromisoformat(rec["created_at"])
                        date_str = dt_obj.strftime("%b %d, %Y — %H:%M UTC")
                    except Exception:
                        date_str = rec["created_at"][:16]

                    hcol1, hcol2 = st.columns([5, 1])
                    with hcol1:
                        st_html(f"""
                        <div class="history-card">
                            <div class="history-card-title">📋 {rec['title']}</div>
                            <div class="history-card-meta">
                                🕐 {date_str} &nbsp;·&nbsp;
                                🔬 {rec['findings_count']} biomarker(s) extracted
                            </div>
                        </div>
                        """)
                        if st.button(f"📂 Restore", key=f"restore_{rec['id']}", use_container_width=True):
                            try:
                                full_rec = _auth.get_report_by_id(rec["id"], _current_user["id"])
                                if full_rec:
                                    restored = HealthReportAnalysis.model_validate_json(full_rec["summary_json"])
                                    st.session_state.analysis_result = restored
                                    st.session_state.chat_history = []
                                    st.toast(f"✅ Restored: {rec['title']}", icon="📂")
                                    st.rerun()
                            except Exception as _re:
                                st.error(f"Could not restore: {_re}")
                    with hcol2:
                        if st.button("🗑️", key=f"del_{rec['id']}", help="Delete this report", use_container_width=True):
                            _auth.delete_report(rec["id"], _current_user["id"])
                            st.session_state._report_history = _auth.get_report_history(_current_user["id"])
                            st.toast("🗑️ Report deleted.", icon="🗑️")
                            st.rerun()

        # ── EXPORT ACTION BUTTONS & WORKSPACE RESET ──
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#334155; margin-bottom:8px;'>📥 Export Report Data & Actions:</p>", unsafe_allow_html=True)
        ex_col1, ex_col2, ex_col3, ex_col4 = st.columns(4)
        with ex_col1:
            try:
                pdf_bytes = generate_pdf_report(analysis)
                st.download_button(
                    label="📥 Export PDF",
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
                label="📋 Export JSON",
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
                label="📝 Export MD",
                data="\n".join(md_lines),
                file_name="Medical_Report_Summary.md",
                mime="text/markdown",
                use_container_width=True
            )
        with ex_col4:
            if st.button("➕ New Analysis", use_container_width=True, help="Clear active report view and start a new analysis"):
                st.session_state.analysis_result = None
                st.session_state.chat_history = []
                st.session_state.history_loaded = False
                st.rerun()

