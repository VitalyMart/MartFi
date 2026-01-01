from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "front" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
