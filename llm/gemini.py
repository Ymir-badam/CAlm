# import os
# import google.generativeai as genai

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# model = genai.GenerativeModel("gemini-2.5-flash")
# import google.generativeai as genai



# from urllib import response
from django.conf import settings
import os
from pathlib import Path

import google.generativeai as genai
import vertexai
from vertexai.generative_models import GenerativeModel
from django.conf import settings

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID =  "ai-resource-490118"
LOCATION   = "us-central1"
MODEL      = "gemini-2.5-flash"  
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
       )

class GeminiLLM:
    def __init__(self):
        
        vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
        self.model = GenerativeModel(MODEL)

    def generate(self, prompt):
        #print(prompt)
        response = self.model.generate_content(prompt)
        return response.text.strip()
 
        # response = self.model.generate_content(prompt)
        # return response.text
def summarize_text(text):
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
    model = GenerativeModel(MODEL)
    prompt = f"Summarize this document clearly:\n\n{text[:8000]}"
    response = model.generate_content(prompt)
    return response.text
