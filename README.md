# Health-Report-Summarizer-AI-Application

An AI-powered medical and health report analysis dashboard built with Streamlit and Google Gemini. It transforms complex medical lab reports into clear, patient-friendly summaries, interactive metric charts, actionable lifestyle recommendations, doctor discussion questions, and downloadable PDF/JSON reports.

## Features

- 📄 **Multi-Format Support**: Upload PDF reports or paste raw lab report text.
- ⚡ **AI Health Intelligence**: Analyzes abnormal vs. normal markers with risk categorizations.
- 📊 **Visual Analytics**: Interactive health score metrics and vital range visualizations.
- 🩺 **Doctor-Ready Questions**: Curated questions to ask your physician during your next consultation.
- 📑 **Export Options**: Download comprehensive structured PDF and JSON reports.
- 🧪 **Sample Reports Included**: Built-in 1-click test reports for quick evaluation.

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Pranavv28/Health-Report-Summarizer-AI-Application.git
   cd Health-Report-Summarizer-AI-Application
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your Google Gemini API key inside `.env`:
   ```env
   GEMINI_API_KEY="your-api-key-here"
   ```

5. **Run the Application:**
   ```bash
   streamlit run streamlit_app.py
   ```

## Disclaimer

This application is for informational and educational purposes only. It is not intended to be a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider with any medical questions.
