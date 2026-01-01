from fastapi import Request, Response
from .templates import templates
from .auth.security import get_csrf_token


def render_form_error(
    request: Request,
    template_name: str,
    error: str,
) -> Response:
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        template_name,
        {"request": request, "error": error, "csrf_token": csrf_token},
    )
