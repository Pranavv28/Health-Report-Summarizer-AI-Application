import io
import json
import time
from typing import List, Dict, Any, Union
from pypdf import PdfReader
from PIL import Image

from google import genai
from google.genai import types

from config import get_api_key, MODEL_NAME, ANALYSIS_SYSTEM_INSTRUCTION
from schema import HealthReportAnalysis

class HealthReportAnalyzer:
    def __init__(self):
        api_key = get_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
        self.client = genai.Client(api_key=api_key)

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Attempt to extract text content directly from PDF bytes."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_content = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
            return "\n".join(text_content).strip()
        except Exception:
            return ""

    def analyze_report(
        self, 
        file_bytes_or_text: Union[bytes, str], 
        file_type: str = "text"
    ) -> HealthReportAnalysis:
        """
        Analyze a health report (raw text, PDF, PNG, or JPG) using Gemini 2.5 Flash
        with structured Pydantic schema output.
        """
        contents = []

        if file_type == "text" or isinstance(file_bytes_or_text, str):
            text_str = file_bytes_or_text if isinstance(file_bytes_or_text, str) else file_bytes_or_text.decode("utf-8", errors="ignore")
            contents.append(f"Please analyze the following health report:\n\n{text_str}")
        
        elif file_type == "pdf" and isinstance(file_bytes_or_text, bytes):
            # Try text extraction first
            extracted_text = self.extract_text_from_pdf(file_bytes_or_text)
            if len(extracted_text) > 50:
                contents.append(f"Please analyze the following PDF health report text:\n\n{extracted_text}")
            else:
                # Scanned PDF or image-only PDF: send as document bytes directly
                pdf_part = types.Part.from_bytes(
                    data=file_bytes_or_text,
                    mime_type="application/pdf"
                )
                contents.append(pdf_part)
                contents.append("Please analyze the document image in this PDF and extract all medical report insights.")
        
        elif file_type in ["png", "jpeg", "jpg"] and isinstance(file_bytes_or_text, bytes):
            mime_type = "image/png" if file_type == "png" else "image/jpeg"
            img_part = types.Part.from_bytes(
                data=file_bytes_or_text,
                mime_type=mime_type
            )
            contents.append(img_part)
            contents.append("Please analyze this medical report image scan and extract all diagnostic lab test parameters.")

        else:
            raise ValueError(f"Unsupported file format: {file_type}")

        # Model retry list — confirmed available on this API key
        models_to_try = [MODEL_NAME, "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
        last_exception = None

        for model in models_to_try:
            for attempt in range(3):  # Up to 3 retries per model for 503 overload
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=ANALYSIS_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            response_schema=HealthReportAnalysis,
                            temperature=0.1,
                        )
                    )

                    if response.parsed and isinstance(response.parsed, HealthReportAnalysis):
                        return response.parsed
                    
                    # Fallback manual Pydantic parsing if SDK response.parsed is None
                    if response.text:
                        cleaned_json = response.text.strip()
                        if cleaned_json.startswith("```json"):
                            cleaned_json = cleaned_json[7:]
                        if cleaned_json.endswith("```"):
                            cleaned_json = cleaned_json[:-3]
                        return HealthReportAnalysis.model_validate_json(cleaned_json)

                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    # Retry on 503 overload with backoff
                    if "503" in err_str or "UNAVAILABLE" in err_str:
                        wait = 2 ** attempt  # 1s, 2s, 4s
                        time.sleep(wait)
                        continue
                    else:
                        break  # Non-retryable error, try next model

        raise RuntimeError(f"Gemini API analysis failed across models: {str(last_exception)}")

    def answer_health_question(
        self, 
        report_summary: str, 
        user_question: str, 
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Provide conversational Q&A assistance based on the analyzed report context.
        """
        history_context = ""
        if chat_history:
            history_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history[-6:]
            ])

        prompt = f"""
System context: You are an empathetic, educational health AI assistant.
The patient is asking a question about their health report summarized below:

--- REPORT SUMMARY ---
{report_summary}
----------------------

Conversation History:
{history_context}

Patient Question: {user_question}

Instructions:
- Provide a clear, supportive answer based on the report summary.
- Avoid giving a definitive diagnosis.
- Remind the user to consult their physician for personal medical decisions.
"""
        try:
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                )
            )
            return response.text.strip() if response.text else "I am unable to answer this question at the moment."
        except Exception as e:
            return f"Error responding to question: {str(e)}"
