import os
from dotenv import load_dotenv

load_dotenv()

class OpenRouterSettings:
    API_KEY = os.getenv("TOKEN_ROUTER")
    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "qwen/qwen-2.5-72b-instruct"
    SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")
    SITE_NAME = os.getenv("SITE_NAME", "MartFi")

openrouter_settings = OpenRouterSettings()