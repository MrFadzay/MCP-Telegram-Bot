import google.generativeai as genai
from typing import List, Dict
from .api import LLMClient
import os


class GoogleClient(LLMClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key is required."
            )
        genai.configure(api_key=self.api_key)
        self._models: List[str] = []

    @property
    def provider_name(self) -> str:
        return "google"

    def get_available_models(self) -> List[str]:
        return self._models

    async def _fetch_models(self) -> None:
        """Fetches the list of available models from the Google AI API."""
        try:
            available_models: List[Dict] = genai.list_models()
            self._models = [
                model.name
                for model in available_models
                if "generateContent" in model.supported_generation_methods
            ]
        except Exception as e:
            print(f"Error fetching models from Google AI API: {e}")
            self._models = ["gemini-2.0-flash"]

    async def generate_response(self, prompt: str, model: str) -> str:
        """Generate a response from the Google Gemini model."""
        try:
            model_instance = genai.GenerativeModel(model_name=model)

            convo = model_instance.start_chat(history=[])
            response = convo.send_message(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Error during response generation: {str(e)}")
