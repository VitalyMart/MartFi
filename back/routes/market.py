from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from ..services.market_service import MarketService
from ..templates import templates
from ..dependencies import get_market_service
from ..dependencies.auth_dependencies import get_current_user
from ..auth.entities.user import User as DomainUser

router = APIRouter()

@router.get("/market")
async def market_default(
    request: Request,
    current_user: DomainUser | None = Depends(get_current_user),
    search: str = Query(""),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    if not current_user:
        return RedirectResponse("/login")
    
    params = {}
    if search:
        params["search"] = search
    if sort_by != "name":
        params["sort_by"] = sort_by
    if sort_order != "asc":
        params["sort_order"] = sort_order
    if page != 1:
        params["page"] = page
    if page_size != 50:
        params["page_size"] = page_size
    
    url = "/market/stock"
    if params:
        url += f"?{urlencode(params)}"
    
    return RedirectResponse(url, status_code=307)

@router.get("/market/{asset_type}")
async def assets_page(
    request: Request,
    asset_type: str,
    market_service: MarketService = Depends(get_market_service),
    current_user: DomainUser | None = Depends(get_current_user),
    search: str = Query(""),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    if not current_user:
        return RedirectResponse("/login")
    
    valid_asset_types = ["stock", "bonds", "funds", "currency", "indices"]
    if asset_type not in valid_asset_types:
        return RedirectResponse("/market/stock")
    
    data = await market_service.get_market_page_data(
        request=request,
        current_user=current_user,
        asset_type=asset_type,
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
            "asset_type": asset_type,
        }
    )

@router.get("/api/market/test/{asset_type}")
async def moex_test(
    asset_type: str,
    market_service: MarketService = Depends(get_market_service)
):
    return await market_service.get_moex_test_data(asset_type)

@router.post("/api/market/refresh/{asset_type}")
async def refresh_market_data(
    asset_type: str,
    market_service: MarketService = Depends(get_market_service),
    current_user: DomainUser | None = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await market_service.refresh_cache(asset_type)

@router.get("/api/market/stocks/{asset_type}")
async def get_stocks_api(
    asset_type: str,
    market_service: MarketService = Depends(get_market_service),
    search: str = Query(""),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: DomainUser | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = await market_service.get_market_stocks_data(
        asset_type=asset_type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "data": data.stocks,
        "pagination": data.pagination,
        "filters": data.filters,
    }