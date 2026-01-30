from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from ..auth.security import csrf_protect
from ..services.portfolio_service import PortfolioService
from ..services.render_service import RenderService
from ..templates import templates
from ..dependencies.portfolio_dependencies import get_portfolio_service
from ..dependencies.auth_dependencies import get_current_user
from ..dependencies.render_dependencies import get_render_service
from ..auth.entities.user import User as DomainUser
from ..core.logger import logger

router = APIRouter()

@router.get("/portfolio")
async def portfolio_page(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    render_service: RenderService = Depends(get_render_service),
    current_user: DomainUser | None = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse("/login")
    
    data = await portfolio_service.get_portfolio_page_data(request, current_user)
    if not data:
        return RedirectResponse("/login")
    
    return render_service.render_with_csrf(
        request=request,
        template_name="portfolio.html",
        context={
            "user": data.user,
            "portfolio_items": data.portfolio_items,
            "portfolio_summary": data.portfolio_summary,
        }
    )

@router.post("/api/portfolio/add")
async def add_to_portfolio(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    current_user: DomainUser | None = Depends(get_current_user),
    ticker: str = Form(...),
    asset_type: str = Form(...),
    quantity: float = Form(...),
    average_price: float = Form(0.0),
    notes: str = Form(""),
    csrf_verified: bool = Depends(csrf_protect),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if asset_type == 'index':
        return JSONResponse({
            "success": False,
            "message": "Индексы нельзя добавлять в портфель"
        }, status_code=400)
    
    try:
        result = await portfolio_service.add_to_portfolio(
            user_id=current_user.id,
            ticker=ticker,
            asset_type=asset_type,
            quantity=quantity,
            average_price=average_price,
            notes=notes
        )
        
        if result:
            return JSONResponse({
                "success": True,
                "message": "Актив добавлен в портфель",
                "data": result
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Ошибка при добавлении актива"
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"Error adding to portfolio: {e}")
        return JSONResponse({
            "success": False,
            "message": "Внутренняя ошибка сервера"
        }, status_code=500)

@router.post("/api/portfolio/remove/{item_id}")
async def remove_from_portfolio(
    request: Request,
    item_id: int,
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    current_user: DomainUser | None = Depends(get_current_user),
    csrf_verified: bool = Depends(csrf_protect),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        success = await portfolio_service.remove_from_portfolio(current_user.id, item_id)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Актив удален из портфеля"
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Актив не найден или ошибка при удалении"
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"Error removing from portfolio: {e}")
        return JSONResponse({
            "success": False,
            "message": "Внутренняя ошибка сервера"
        }, status_code=500)

@router.get("/api/portfolio/stats")
async def get_portfolio_stats(
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    current_user: DomainUser | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await portfolio_service.get_portfolio_page_data(None, current_user)
        return JSONResponse({
            "success": True,
            "data": data.portfolio_summary if data else {}
        })
    except Exception as e:
        logger.error(f"Error getting portfolio stats: {e}")
        return JSONResponse({
            "success": False,
            "message": "Ошибка при получении статистики"
        }, status_code=500)