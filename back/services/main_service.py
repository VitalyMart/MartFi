from typing import Optional
from ..database.models import User
from ..contracts.security import ISecurityService
from ..dto.market import MainPageData


class MainService:
    def __init__(self, security_service: ISecurityService):
        self.security_service = security_service

    async def get_main_page_data(self, request, current_user: Optional[User]) -> Optional[MainPageData]:
        if not current_user:
            return None

        csrf_token = await self.security_service.get_csrf_token(request)

        return MainPageData(user=current_user, csrf_token=csrf_token)
