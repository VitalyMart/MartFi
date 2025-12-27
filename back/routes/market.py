from fastapi import APIRouter, Depends, Request
from typing import Callable

from ..dependencies import get_market_page_context_service, get_market_service

router = APIRouter()

@router.get("/market")
async def assets_page(
    request: Request,
    get_context: Callable = Depends(get_market_page_context_service),
):
    return await get_context(request)

@router.get("/api/moex-test")
async def moex_test(
    market_service = Depends(get_market_service),
):
    return await market_service.get_moex_test_data()