from fastapi import APIRouter, Depends, Request, Query, HTTPException
from typing import Optional

from ..dependencies import get_market_page_context_service, get_market_service
from ..auth.dependencies import get_current_user
from ..database.models import User

router = APIRouter()

@router.get("/market")
async def assets_page(
    request: Request,
    search: Optional[str] = Query("", description="Поисковый запрос"),
    sort_by: Optional[str] = Query("name", description="Поле для сортировки (name, ticker, price, change, change_percent, volume)"),
    sort_order: Optional[str] = Query("asc", description="Порядок сортировки (asc, desc)"),
    page: Optional[int] = Query(1, ge=1, description="Номер страницы"),
    page_size: Optional[int] = Query(50, ge=1, le=200, description="Размер страницы"),
    get_context=Depends(get_market_page_context_service),
):
    return await get_context(
        request=request,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

@router.get("/api/market/test")
async def moex_test(
    market_service = Depends(get_market_service)
):
    """Тестовый эндпоинт для проверки подключения к MOEX"""
    return await market_service.get_moex_test_data()

@router.post("/api/market/refresh")
async def refresh_market_data(
    market_service = Depends(get_market_service),
    current_user: User = Depends(get_current_user)
):
    """Принудительно обновляет кэш рыночных данных"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await market_service.refresh_cache()

@router.get("/api/market/stocks")
async def get_stocks_api(
    market_service = Depends(get_market_service),
    search: Optional[str] = Query("", description="Поисковый запрос"),
    sort_by: Optional[str] = Query("name", description="Поле для сортировки"),
    sort_order: Optional[str] = Query("asc", description="Порядок сортировки"),
    page: Optional[int] = Query(1, ge=1, description="Номер страницы"),
    page_size: Optional[int] = Query(50, ge=1, le=100, description="Размер страницы"),
    current_user: User = Depends(get_current_user)
):
    """API для получения отфильтрованных акций (JSON)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    all_stocks = await market_service.get_cached_stocks()
    
    
    filtered_stocks = market_service._filter_stocks(all_stocks, search)
    sorted_stocks = market_service._sort_stocks(filtered_stocks, sort_by, sort_order)
    
    
    total_count = len(sorted_stocks)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_stocks = sorted_stocks[start_idx:end_idx]
    
    return {
        "success": True,
        "data": paginated_stocks,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        },
        "filters": {
            "search": search,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
    }