from fastapi.templating import Jinja2Templates

_templates = None

def set_templates(templates: Jinja2Templates):
    global _templates
    _templates = templates

def get_templates():
    if _templates is None:
        raise RuntimeError("Templates not initialized")
    return _templates