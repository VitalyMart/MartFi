import aiohttp
from datetime import datetime
from typing import List, Dict, Any
from fastapi import Request
from ..core.logger import logger
from ..contracts.security import ISecurityService


class MarketService:
    def __init__(self, security_service: ISecurityService):
        self.security_service = security_service
    
    async def get_market_page_context(
        self,
        request: Request,
        current_user: Any
    ) -> Dict[str, Any]:
        from fastapi.responses import RedirectResponse
        from ..templates import templates
        
        if not current_user:
            return RedirectResponse("/login")
        
        csrf_token = await self.security_service.get_csrf_token(request)
        stocks = await self.fetch_stocks()
        
        return templates.TemplateResponse(
            "market.html",
            {
                "request": request,
                "user": current_user,
                "csrf_token": csrf_token,
                "stocks": stocks
            }
        )
    
    async def get_moex_test_data(self) -> Dict[str, Any]:
        stocks = await self._fetch_moex_data()
        return {
            "message": "MOEX data fetched successfully",
            "stocks_count": len(stocks),
            "stocks": stocks
        }
    
    async def fetch_stocks(self) -> List[Dict[str, Any]]:
        try:
            url = (
                "https://iss.moex.com/iss/engines/stock/"
                "markets/shares/boards/TQBR/securities.json"
            )
            
            async with aiohttp.ClientSession() as session:
                securities_url = (
                    f"{url}?iss.meta=off&"
                    "securities.columns=SECID,SHORTNAME,SECNAME"
                )
                async with session.get(securities_url) as response:
                    data = await response.json()
                    securities = data.get('securities', {}).get('data', [])
                
                marketdata_url = url.replace(
                    "securities.json",
                    "securities.json?iss.only=marketdata&"
                    "marketdata.columns=SECID,LAST,LASTTOPREVPRICE"
                )
                async with session.get(marketdata_url) as response:
                    marketdata = await response.json()
                    quotes = marketdata.get('marketdata', {}).get('data', [])
                
                quotes_dict = {}
                for quote in quotes:
                    if quote and len(quote) >= 3:
                        ticker = quote[0]
                        last_price = quote[1] if quote[1] is not None else 0
                        change = quote[2] if quote[2] is not None else 0
                        quotes_dict[ticker] = {
                            'price': float(last_price),
                            'change': float(change)
                        }
                
                result = []
                for security in securities[:1000]:
                    if not security or len(security) < 3:
                        continue
                    
                    ticker = security[0]
                    short_name = security[1]
                    full_name = security[2]
                    
                    quote = quotes_dict.get(ticker, {'price': 0, 'change': 0})
                    
                    result.append({
                        'ticker': ticker,
                        'name': short_name,
                        'full_name': full_name,
                        'price': quote['price'],
                        'change': quote['change'],
                        'updated_at': datetime.now().isoformat()
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error in fetch_stocks: {e}")
            return []
    
    async def _fetch_moex_data(self) -> List[Dict[str, Any]]:
        try:
            url = (
                "https://iss.moex.com/iss/engines/stock/"
                "markets/shares/boards/TQBR/securities.json"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    securities = data.get('securities', {}).get('data', [])
                    marketdata = data.get('marketdata', {}).get('data', [])
                    parsed_stocks = []
                    
                    for i, security in enumerate(securities[:25]):
                        ticker = security[0] if security else "N/A"
                        name = security[2] if len(security) > 2 else "N/A"
                        price = 0
                        change = 0
                        
                        if i < len(marketdata):
                            price = marketdata[i][12] if len(marketdata[i]) > 12 else 0
                            change = marketdata[i][14] if len(marketdata[i]) > 14 else 0
                        
                        stock_data = {
                            'ticker': ticker,
                            'name': name,
                            'price': price,
                            'change': change
                        }
                        parsed_stocks.append(stock_data)
                    
                    return parsed_stocks
                    
        except Exception as e:
            logger.error(f"Error fetching MOEX data: {e}")
            return []