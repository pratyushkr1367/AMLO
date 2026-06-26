"""Quick diagnostic — lists all Gemini models available to this API key."""
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("All available models:\n")
for m in client.models.list():
    print(m.name)
