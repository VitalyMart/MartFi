from typing import Optional, Dict, Any
from fastapi import Request, Response
from fastapi.templating import Jinja2Templates
from ..auth.security import get_csrf_token


class RenderService:
    def __init__(self, templates: Jinja2Templates):
        self.templates = templates

    def render_form_error(
        self,
        request: Request,
        template_name: str,
        error: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Response:
        context = {
            "request": request,
            "error": error,
            "csrf_token": get_csrf_token(request),
        }
        if additional_context:
            context.update(additional_context)
        
        return self.templates.TemplateResponse(template_name, context)

    def render_with_csrf(
        self,
        request: Request,
        template_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Response:
        full_context = {
            "request": request,
            "csrf_token": get_csrf_token(request),
        }
        if context:
            full_context.update(context)
        
        return self.templates.TemplateResponse(template_name, full_context)