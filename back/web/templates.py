from fastapi.templating import Jinja2Templates
import os

def setup_templates(frontend_path: str) -> Jinja2Templates:
    pages_path = os.path.join(frontend_path, "templates")
    return Jinja2Templates(directory=pages_path)