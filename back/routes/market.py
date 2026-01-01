from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional

from ..services.market_service import MarketService
from ..templates import templates
from ..dependencies import get_market_service
from ..auth.dependencies import get_current_user
from ..database.models import User

router = APIRouter()


@router.get("/market")
async def assets_page(
    request: Request,
    market_service: MarketService = Depends(get_market_service),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query("", description="Поисковый запрос"),
    sort_by: Optional[str] = Query(
        "name", description="Поле для сортировки (name, ticker, price, change, change_percent, volume)"
    ),
    sort_order: Optional[str] = Query("asc", description="Порядок сортировки (asc, desc)"),
    page: Optional[int] = Query(1, ge=1, description="Номер страницы"),
    page_size: Optional[int] = Query(50, ge=1, le=200, description="Размер страницы"),
):
    if not current_user:
        return RedirectResponse("/login")

    data = await market_service.get_market_page_data(
        request=request,
        current_user=current_user,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    if not data:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "market.html",
        {
            "request": request,
            "user": data.user,
            "csrf_token": data.csrf_token,
            "stocks": data.stocks,
            "search_query": data.search_query,
            "sort_by": data.sort_by,
            "sort_order": data.sort_order,
            "page": data.page,
            "total_pages": data.total_pages,
            "total_count": data.total_count,
        },
    )


@router.get("/api/market/test")
async def moex_test(market_service: MarketService = Depends(get_market_service)):
    return await market_service.get_moex_test_data()


@router.post("/api/market/refresh")
async def refresh_market_data(
    market_service: MarketService = Depends(get_market_service), current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return await market_service.refresh_cache()


@router.get("/api/market/stocks")
async def get_stocks_api(
    market_service: MarketService = Depends(get_market_service),
    search: Optional[str] = Query("", description="Поисковый запрос"),
    sort_by: Optional[str] = Query("name", description="Поле для сортировки"),
    sort_order: Optional[str] = Query("asc", description="Порядок сортировки"),
    page: Optional[int] = Query(1, ge=1, description="Номер страницы"),
    page_size: Optional[int] = Query(50, ge=1, le=100, description="Размер страницы"),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await market_service.get_market_stocks_data(
        search=search, sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size
    )

    return {"success": True, "data": data.stocks, "pagination": data.pagination, "filters": data.filters}
