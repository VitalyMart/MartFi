import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..core import redis_client
from ..core.logger import logger
from ..contracts.security import ISecurityService
from ..templates import templates

class MarketService:
    def __init__(self, security_service: ISecurityService):
        self.security_service = security_service
        self.moex_base_url = "https://iss.moex.com/iss"
        self.cache_ttl = 300  
    
    async def get_market_page_context(
        self,
        request: Request,
        current_user: Any,
        search: str = "",
        sort_by: str = "name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:

        
        if not current_user:
            return RedirectResponse("/login")
        
        csrf_token = await self.security_service.get_csrf_token(request)
        
        
        all_stocks = await self.get_cached_stocks()
        
        
        filtered_stocks = self._filter_stocks(all_stocks, search)
        sorted_stocks = self._sort_stocks(filtered_stocks, sort_by, sort_order)
        
        
        total_count = len(sorted_stocks)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_stocks = sorted_stocks[start_idx:end_idx]
        
        return templates.TemplateResponse(
            "market.html",
            {
                "request": request,
                "user": current_user,
                "csrf_token": csrf_token,
                "stocks": paginated_stocks,
                "search_query": search,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "page": page,
                "total_pages": (total_count + page_size - 1) // page_size,
                "total_count": total_count
            }
        )
    
    async def get_cached_stocks(self) -> List[Dict[str, Any]]:
        """Получает акции из кэша или API MOEX"""
        cache_key = "moex:stocks"
        
        try:
            
            cached_data = redis_client.get(cache_key)
            if cached_data:
                stocks = json.loads(cached_data)
                logger.info(f"Loaded {len(stocks)} stocks from cache")
                return stocks
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
        
        
        stocks = await self._fetch_all_stocks()
        
        
        try:
            redis_client.setex(cache_key, self.cache_ttl, json.dumps(stocks))
            logger.info(f"Cached {len(stocks)} stocks for {self.cache_ttl} seconds")
        except Exception as e:
            logger.error(f"Error caching stocks: {e}")
        
        return stocks
    
    async def _fetch_all_stocks(self) -> List[Dict[str, Any]]:
        """Получает все акции с MOEX"""
        try:
            url = f"{self.moex_base_url}/engines/stock/markets/shares/boards/TQBR/securities.json"
            
            async with aiohttp.ClientSession() as session:
                
                securities_params = {
                    'iss.meta': 'off',
                    'securities.columns': 'SECID,SHORTNAME,SECNAME,ISIN,REGNUMBER,LOTSIZE'
                }
                
                async with session.get(url, params=securities_params) as response:
                    if response.status != 200:
                        logger.error(f"MOEX API error: {response.status}")
                        return self._get_fallback_stocks()
                    
                    data = await response.json()
                    securities = data.get('securities', {}).get('data', [])
                
                
                marketdata_params = {
                    'iss.meta': 'off',
                    'marketdata.columns': 'SECID,LAST,LASTTOPREVPRICE,OPEN,CHANGE,VALUE,UPDATETIME'
                }
                
                marketdata_url = url.replace('securities.json', 'securities.json?iss.only=marketdata')
                async with session.get(marketdata_url, params=marketdata_params) as response:
                    if response.status != 200:
                        logger.error(f"MOEX marketdata error: {response.status}")
                        return self._parse_securities_only(securities)
                    
                    marketdata = await response.json()
                    market_data = marketdata.get('marketdata', {}).get('data', [])
                
                
                market_dict = {}
                for item in market_data:
                    if item and len(item) >= 7:
                        ticker = item[0]
                        market_dict[ticker] = {
                            'price': float(item[1]) if item[1] is not None else 0,
                            'change': float(item[2]) if item[2] is not None else 0,
                            'open': float(item[3]) if item[3] is not None else 0,
                            'change_percent': float(item[4]) if item[4] is not None else 0,
                            'volume': float(item[5]) if item[5] is not None else 0,
                            'update_time': item[6] if len(item) > 6 else None
                        }
                
                
                result = []
                for security in securities[:500]:  
                    if not security or len(security) < 6:
                        continue
                    
                    ticker = security[0]
                    name = security[1]
                    full_name = security[2]
                    isin = security[3] if len(security) > 3 else None
                    regnumber = security[4] if len(security) > 4 else None
                    lotsize = int(security[5]) if len(security) > 5 and security[5] else 1
                    
                    market_info = market_dict.get(ticker, {
                        'price': 0,
                        'change': 0,
                        'open': 0,
                        'change_percent': 0,
                        'volume': 0,
                        'update_time': None
                    })
                    
                    result.append({
                        'ticker': ticker,
                        'name': name,
                        'full_name': full_name,
                        'price': market_info['price'],
                        'change': market_info['change'],
                        'open_price': market_info['open'],
                        'change_percent': market_info['change_percent'],
                        'volume': market_info['volume'],
                        'update_time': market_info['update_time'],
                        'isin': isin,
                        'regnumber': regnumber,
                        'lotsize': lotsize,
                        'last_updated': datetime.now().isoformat()
                    })
                
                logger.info(f"Fetched {len(result)} stocks from MOEX")
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching MOEX data: {e}")
            return self._get_fallback_stocks()
        except Exception as e:
            logger.error(f"Error fetching stocks: {e}")
            return self._get_fallback_stocks()
    
    def _parse_securities_only(self, securities: List) -> List[Dict[str, Any]]:
        """Парсит только данные о бумагах без рыночных данных"""
        result = []
        for security in securities[:200]:
            if not security or len(security) < 3:
                continue
            
            result.append({
                'ticker': security[0],
                'name': security[1],
                'full_name': security[2],
                'price': 0,
                'change': 0,
                'open_price': 0,
                'change_percent': 0,
                'volume': 0,
                'update_time': None,
                'isin': security[3] if len(security) > 3 else None,
                'regnumber': security[4] if len(security) > 4 else None,
                'lotsize': int(security[5]) if len(security) > 5 and security[5] else 1,
                'last_updated': datetime.now().isoformat()
            })
        
        return result
    
    def _get_fallback_stocks(self) -> List[Dict[str, Any]]:
        """Возвращает тестовые данные если MOEX недоступен"""
        return [
            {
                'ticker': 'SBER',
                'name': 'Сбербанк',
                'full_name': 'Сбербанк России ПАО ао',
                'price': 300.50,
                'change': 5.20,
                'open_price': 295.30,
                'change_percent': 1.73,
                'volume': 15000000,
                'update_time': '10:30:45',
                'isin': 'RU0009029540',
                'regnumber': '1-01-00100-A',
                'lotsize': 10,
                'last_updated': datetime.now().isoformat()
            },
            {
                'ticker': 'GAZP',
                'name': 'Газпром',
                'full_name': 'Газпром ПАО ао',
                'price': 180.30,
                'change': -2.10,
                'open_price': 182.40,
                'change_percent': -1.15,
                'volume': 8000000,
                'update_time': '10:31:20',
                'isin': 'RU0007661625',
                'regnumber': '1-02-00028-A',
                'lotsize': 10,
                'last_updated': datetime.now().isoformat()
            },
            {
                'ticker': 'VTBR',
                'name': 'ВТБ',
                'full_name': 'ВТБ Банк ПАО ао',
                'price': 0.027,
                'change': 0.001,
                'open_price': 0.026,
                'change_percent': 3.85,
                'volume': 500000000,
                'update_time': '10:32:15',
                'isin': 'RU000A0JP5V6',
                'regnumber': '1-01-00106-D',
                'lotsize': 10000,
                'last_updated': datetime.now().isoformat()
            },
            {
                'ticker': 'LKOH',
                'name': 'ЛУКОЙЛ',
                'full_name': 'ЛУКОЙЛ ПАО ао',
                'price': 7500.00,
                'change': 150.00,
                'open_price': 7350.00,
                'change_percent': 2.04,
                'volume': 500000,
                'update_time': '10:33:00',
                'isin': 'RU0009024277',
                'regnumber': '1-01-00056-A',
                'lotsize': 1,
                'last_updated': datetime.now().isoformat()
            },
            {
                'ticker': 'YNDX',
                'name': 'Яндекс',
                'full_name': 'Яндекс Н.В. ао',
                'price': 3500.00,
                'change': -50.00,
                'open_price': 3550.00,
                'change_percent': -1.41,
                'volume': 200000,
                'update_time': '10:34:30',
                'isin': 'NL0009805522',
                'regnumber': '1-01-55078-E',
                'lotsize': 1,
                'last_updated': datetime.now().isoformat()
            }
        ]
    
    def _filter_stocks(self, stocks: List[Dict[str, Any]], search: str) -> List[Dict[str, Any]]:
        """Фильтрует акции по поисковому запросу"""
        if not search:
            return stocks
        
        search_term = search.lower().strip()
        return [
            stock for stock in stocks
            if (search_term in stock.get('name', '').lower() or
                search_term in stock.get('ticker', '').lower() or
                search_term in stock.get('full_name', '').lower() or
                search_term in str(stock.get('isin', '')).lower())
        ]
    
    def _sort_stocks(self, stocks: List[Dict[str, Any]], sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
        """Сортирует акции"""
        if not stocks:
            return stocks
        
        reverse = sort_order.lower() == "desc"
        
        if sort_by == "name":
            return sorted(stocks, key=lambda x: x.get('name', '').lower(), reverse=reverse)
        elif sort_by == "ticker":
            return sorted(stocks, key=lambda x: x.get('ticker', '').lower(), reverse=reverse)
        elif sort_by == "price":
            return sorted(stocks, key=lambda x: float(x.get('price', 0)), reverse=reverse)
        elif sort_by == "change":
            return sorted(stocks, key=lambda x: float(x.get('change', 0)), reverse=reverse)
        elif sort_by == "change_percent":
            return sorted(stocks, key=lambda x: float(x.get('change_percent', 0)), reverse=reverse)
        elif sort_by == "volume":
            return sorted(stocks, key=lambda x: float(x.get('volume', 0)), reverse=reverse)
        else:
            return stocks
    
    async def refresh_cache(self) -> Dict[str, Any]:
        """Принудительно обновляет кэш"""
        try:
            stocks = await self._fetch_all_stocks()
            cache_key = "moex:stocks"
            redis_client.setex(cache_key, self.cache_ttl, json.dumps(stocks))
            
            return {
                "success": True,
                "message": "Cache refreshed successfully",
                "stocks_count": len(stocks),
                "cached_until": (datetime.now() + timedelta(seconds=self.cache_ttl)).isoformat()
            }
        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")
            return {
                "success": False,
                "message": f"Error refreshing cache: {str(e)}"
            }
    
    async def get_moex_test_data(self) -> Dict[str, Any]:
        """Тестовый эндпоинт для проверки API MOEX"""
        try:
            stocks = await self._fetch_all_stocks()
            return {
                "success": True,
                "message": "MOEX data fetched successfully",
                "stocks_count": len(stocks),
                "stocks_sample": stocks[:10] if stocks else []
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching MOEX data: {str(e)}",
                "stocks_count": 0,
                "stocks_sample": []
            }