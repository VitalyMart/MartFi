from fastapi import Depends
from ..templates import templates
from ..services.render_service import RenderService


def get_render_service() -> RenderService:
    return RenderService(templates=templates)