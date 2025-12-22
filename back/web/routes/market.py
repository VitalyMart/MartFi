from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Annotated

from ...auth.security import get_csrf_token
from ...market.services import fetch_moex_data, fetch_stocks
from ...database import get_db
from ...database.models import User
from ...auth.dependencies import get_current_user
from ...web.dependencies import get_templates

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/market")
async def assets_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates)
):
    if not current_user:
        return RedirectResponse("/login")
    
    csrf_token = get_csrf_token(request)
    stocks = await fetch_stocks()
    
    return templates.TemplateResponse(
        "market.html",
        {
            "request": request,
            "user": current_user,
            "csrf_token": csrf_token,
            "stocks": stocks
        }
    )


@router.get("/api/moex-test")
async def moex_test(request: Request):
    stocks = await fetch_moex_data()

    return {
        "message": "MOEX data fetched successfully",
        "stocks_count": len(stocks),
        "stocks": stocks
    }