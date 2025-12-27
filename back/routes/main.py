from fastapi import APIRouter, Depends, Request
from typing import Callable

from ..dependencies import get_main_page_context_service

router = APIRouter()

@router.get("/")
async def root(
    request: Request,
    get_context: Callable = Depends(get_main_page_context_service),
):
    return await get_context(request)