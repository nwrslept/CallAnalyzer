import os
import json
import google.generativeai as genai
from src.config import Config


class AIProcessor:
    """
    Handles interaction with Google Gemini API.
    Responsible for:
    - Audio transcription
    - Sentiment analysis
    - Scoring logic based on the provided criteria
    """

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("Gemini API Key is missing in Config!")

        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def analyze_call(self, audio_path: str) -> dict:
        """
        Uploads audio to Gemini and requests a structured JSON analysis.

        Returns a dictionary with:
        - transcription (str)
        - service_type (str)
        - manager_score (int 1-10)
        - is_rude_or_incorrect (bool)
        - comments (str) - formatted for the 'red' alert if needed
        - points_greeting (0/1)
        - points_closing (0/1)
        """

        print(f"DEBUG: Uploading {audio_path} to Gemini for analysis...")

        audio_file = genai.upload_file(path=audio_path)

        services_str = ", ".join(Config.SERVICES_LIST)

        prompt = f"""
        You are a QA (Quality Assurance) specialist analyzing a client call in Ukrainian.

        Task 1: Transcribe the audio (Ukrainian).
        Task 2: Identify the 'Service Type' strictly from this list: [{services_str}]. If not clear, use "Інше".
        Task 3: Rate the manager's performance (1-10).
        Task 4: Detect if the manager was rude, incorrect, or gave poor answers. Set 'is_critical_fail' to true if yes.
        Task 5: Assign points (1 for Yes, 0 for No):
           - Did the manager greet the client properly?
           - Did the manager close the conversation properly?

        Output format: STRICT JSON (no markdown formatting).
        Structure:
        {{
            "transcription": "Full text of the conversation...",
            "service_type": "Exact string from the list",
            "manager_score": 8,
            "is_critical_fail": false,
            "critical_comment": "Description of why it failed (or empty if OK)",
            "greeting_point": 1,
            "closing_point": 1
        }}
        """

        print("DEBUG: Waiting for Gemini response...")
        response = self.model.generate_content([prompt, audio_file])

        try:
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]

            data = json.loads(text_response)
            return data

        except json.JSONDecodeError:
            print(f"ERROR: Failed to parse JSON from AI response: {response.text}")
            return {
                "transcription": response.text,
                "service_type": "Error",
                "manager_score": 0,
                "is_critical_fail": True,
                "critical_comment": "AI Parse Error",
                "greeting_point": 0,
                "closing_point": 0
            }
