import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..core import redis_client
from ..core.logger import logger
from ..contracts.security import ISecurityService
from ..contracts.market import IMarketDataProvider
from ..dto.market import MarketPageData, MarketStocksData
from ..config import settings


class MarketService:
    def __init__(
        self,
        security_service: ISecurityService,
        data_providers: List[IMarketDataProvider],
    ):
        self.security_service = security_service
        self.data_providers = data_providers
        self.cache_ttl = 300

    async def get_cached_data(self, asset_type: str) -> List[Dict[str, Any]]:
        provider = self._get_provider(asset_type)
        if not provider:
            logger.warning(f"Unknown asset type: {asset_type}")
            return []

        cache_key = provider.get_cache_key()
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"Loaded {len(data)} {asset_type} from cache")
                return data
        except Exception as e:
            logger.error(f"Error reading {asset_type} from cache: {e}")

        data = await provider.fetch_data()
        try:
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(data))
            logger.info(f"Cached {len(data)} {asset_type} for {self.cache_ttl} seconds")
        except Exception as e:
            logger.error(f"Error caching {asset_type}: {e}")

        return data

    async def get_all_cached_data(self) -> Dict[str, List[Dict[str, Any]]]:
        result = {}
        for provider in self.data_providers:
            asset_type = provider.get_asset_type()
            data = await self.get_cached_data(asset_type)
            result[asset_type] = data
        return result

    def _get_provider(self, asset_type: str) -> Optional[IMarketDataProvider]:
        for p in self.data_providers:
            if p.get_asset_type() == asset_type:
                return p
        return None

    def _filter_data(self, data: List[Dict[str, Any]], search: str) -> List[Dict[str, Any]]:
        if not search:
            return data
        term = search.lower().strip()
        return [
            item for item in data
            if (
                term in item.get('name', '').lower()
                or term in item.get('ticker', '').lower()
                or term in item.get('full_name', '').lower()
                or term in str(item.get('isin', '')).lower()
            )
        ]

    def _sort_data(self, data: List[Dict[str, Any]], sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
        if not data:
            return data
        reverse = sort_order.lower() == "desc"
        sort_key_map = {
            "name": lambda x: x.get('name', '').lower(),
            "ticker": lambda x: x.get('ticker', '').lower(),
            "price": lambda x: float(x.get('price', 0)),
            "change": lambda x: float(x.get('change', 0)),
            "change_percent": lambda x: float(x.get('change_percent', 0)),
            "volume": lambda x: float(x.get('volume', 0)),
            "yield": lambda x: float(x.get('yield', 0)),
            "coupon_value": lambda x: float(x.get('coupon_value', 0)),
        }
        key_func = sort_key_map.get(sort_by, sort_key_map["name"])
        return sorted(data, key=key_func, reverse=reverse)

    def _paginate(self, data: List[Dict[str, Any]], page: int, page_size: int):
        total_count = len(data)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = data[start_idx:end_idx]
        total_pages = (total_count + page_size - 1) // page_size
        return type('Page', (), {
            'items': paginated_items,
            'total_count': total_count,
            'total_pages': total_pages,
        })()

    async def get_market_page_data(
        self,
        request,
        current_user: Any,
        asset_type: str = "stock",
        search: str = "",
        sort_by: str = "name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> Optional[MarketPageData]:
        if not current_user:
            return None
        csrf_token = await self.security_service.get_csrf_token(request)
        all_data = await self.get_cached_data(asset_type)
        filtered_and_sorted = self._filter_data(all_data, search)
        sorted_data = self._sort_data(filtered_and_sorted, sort_by, sort_order)
        paginated = self._paginate(sorted_data, page, page_size)
        return MarketPageData(
            user=current_user,
            csrf_token=csrf_token,
            stocks=paginated.items,
            search_query=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            total_pages=paginated.total_pages,
            total_count=paginated.total_count,
        )

    async def get_market_stocks_data(
        self,
        asset_type: str,
        search: str = "",
        sort_by: str = "name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> MarketStocksData:
        all_data = await self.get_cached_data(asset_type)
        filtered_and_sorted = self._filter_data(all_data, search)
        sorted_data = self._sort_data(filtered_and_sorted, sort_by, sort_order)
        total_count = len(sorted_data)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_stocks = sorted_data[start_idx:end_idx]
        total_pages = (total_count + page_size - 1) // page_size
        return MarketStocksData(
            stocks=paginated_stocks,
            pagination={
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
            },
            filters={"search": search, "sort_by": sort_by, "sort_order": sort_order, "asset_type": asset_type},
        )

    async def refresh_cache(self, asset_type: str = "stock") -> Dict[str, Any]:
        provider = self._get_provider(asset_type)
        if not provider:
            return {"success": False, "message": f"Invalid asset type: {asset_type}"}
        try:
            data = await provider.fetch_data()
            cache_key = provider.get_cache_key()
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(data))
            return {
                "success": True,
                "message": f"{asset_type.capitalize()} cache refreshed successfully",
                "count": len(data),
                "cached_until": (datetime.now() + timedelta(seconds=self.cache_ttl)).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error refreshing {asset_type} cache: {e}")
            return {"success": False, "message": f"Error refreshing {asset_type} cache: {str(e)}"}

    async def get_moex_test_data(self, asset_type: str = "stock") -> Dict[str, Any]:
        provider = self._get_provider(asset_type)
        if not provider:
            return {"success": False, "message": f"Invalid asset type: {asset_type}"}
        try:
            data = await provider.fetch_data()
            return {
                "success": True,
                "message": f"{asset_type.capitalize()} data fetched successfully",
                "count": len(data),
                "sample": data[:10] if data else [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching {asset_type} data: {str(e)}",
                "count": 0,
                "sample": [],
            }