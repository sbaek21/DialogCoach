from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# API Configuration
MODEL_NAME = "gemini-2.5-flash-lite"