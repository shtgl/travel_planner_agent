import os
from dotenv import load_dotenv

load_dotenv()

class DefaultConfig:
    GEMINI_MODEL = "gemini-2.0-flash"
    GEMINI_KEY = os.getenv("GEMINI_KEY")
