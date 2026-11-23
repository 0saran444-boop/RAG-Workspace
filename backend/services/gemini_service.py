import time
import google.generativeai as genai
from backend.config import Config

if Config.GOOGLE_API_KEY:
    genai.configure(api_key=Config.GOOGLE_API_KEY)

class GeminiService:
    def __init__(self, model_name="gemini-3.5-flash-lite"):
        if not Config.GOOGLE_API_KEY:
            raise ValueError(
                "Gemini/Google API key is not configured. Please set GOOGLE_API_KEY or GEMINI_API_KEY in your .env file."
            )
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(model_name)

    def generate_chat_response(self, prompt: str) -> str:
        max_retries = 3
        wait_time = 10  # seconds to wait if rate-limited
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2  # Exponential backoff
                    continue
                raise e

    def generate_rag_response(self, context: str, question: str) -> str:
        prompt = f"""You are a precise RAG assistant. Use the provided context to answer the user's question. 
Format your response strictly as 5 numbered lines (1, 2, 3, 4, 5).
- Lines 1 to 4: Key factual points answering the question based on the context.
- Line 5: "Source: [filename]" indicating the source document.
If the answer cannot be found in the context, output 5 lines stating that the answer is not found, with line 5 as "Source: None".

Context:
{context}

Question:
{question}

Answer (strictly 5 lines):"""
        return self.generate_chat_response(prompt)