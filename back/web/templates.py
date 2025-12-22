from fastapi.templating import Jinja2Templates
from pathlib import Path

def setup_templates(frontend_dir: str) -> Jinja2Templates:
    templates_dir = Path(frontend_dir) / "templates"
    return Jinja2Templates(directory=str(templates_dir))