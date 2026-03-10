import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any
from back.contracts.market import IMarketDataProvider
from back.core.logger import logger

class StocksDataProvider(IMarketDataProvider):
    def __init__(self, moex_base_url: str):
        self.moex_base_url = moex_base_url.rstrip()

    def get_cache_key(self) -> str:
        return "moex:stocks"

    def get_asset_type(self) -> str:
        return "stock"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.moex_base_url}/engines/stock/markets/shares/boards/TQBR/securities.json"
            async with aiohttp.ClientSession() as session:
                securities_params = {
                    'iss.meta': 'off',
                    'securities.columns': 'SECID,SHORTNAME,SECNAME,ISIN,REGNUMBER,LOTSIZE,PREVPRICE',
                }
                async with session.get(url, params=securities_params) as response:
                    if response.status != 200:
                        logger.error(f"MOEX API error: {response.status}")
                        return []
                    data = await response.json()
                    securities = data.get('securities', {}).get('data', [])

                marketdata_params = {
                    'iss.meta': 'off',
                    'marketdata.columns': 'SECID,LAST,CHANGE,UPDATETIME',
                }
                marketdata_url = url + "?iss.only=marketdata"
                async with session.get(marketdata_url, params=marketdata_params) as response:
                    if response.status != 200:
                        logger.error(f"MOEX marketdata error: {response.status}")
                        return self._parse_securities_only(securities)
                    marketdata = await response.json()
                    market_data = marketdata.get('marketdata', {}).get('data', [])

                security_dict = {}
                for security in securities:
                    if security and len(security) >= 7:
                        ticker = security[0]
                        security_dict[ticker] = {
                            'name': security[1],
                            'full_name': security[2],
                            'isin': security[3] if len(security) > 3 else None,
                            'regnumber': security[4] if len(security) > 4 else None,
                            'lotsize': int(security[5]) if len(security) > 5 and security[5] else 1,
                            'prev_price': float(security[6]) if len(security) > 6 and security[6] is not None else 0,
                        }

                market_dict = {}
                for item in market_data:
                    if item and len(item) >= 4:
                        ticker = item[0]
                        last_price = float(item[1]) if item[1] is not None else 0
                        
                        if ticker in security_dict:
                            prev_price = security_dict[ticker]['prev_price']
                            if prev_price != 0:
                                change_rub = last_price - prev_price
                                change_percent = (change_rub / prev_price) * 100
                            else:
                                change_rub = 0
                                change_percent = 0
                            
                            market_dict[ticker] = {
                                'price': last_price,
                                'change': change_rub,
                                'open_price': prev_price,
                                'change_percent': change_percent,
                                'volume': 0,
                                'update_time': item[3] if len(item) > 3 else None,
                            }

                result = []
                for ticker, sec_info in security_dict.items():
                    market_info = market_dict.get(
                        ticker,
                        {
                            'price': 0,
                            'change': 0,
                            'open_price': sec_info['prev_price'],
                            'change_percent': 0,
                            'volume': 0,
                            'update_time': None
                        },
                    )
                    
                    result.append({
                        'ticker': ticker,
                        'name': sec_info['name'],
                        'full_name': sec_info['full_name'],
                        'price': market_info['price'],
                        'change': round(market_info['change'], 4),
                        'open_price': market_info['open_price'],
                        'change_percent': round(market_info['change_percent'], 2),
                        'volume': market_info['volume'],
                        'update_time': market_info['update_time'],
                        'isin': sec_info['isin'],
                        'regnumber': sec_info['regnumber'],
                        'lotsize': sec_info['lotsize'],
                        'last_updated': datetime.now().isoformat(),
                    })
                
                logger.info(f"Fetched {len(result)} stocks from MOEX")
                return result[:500]

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching MOEX data: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching stocks: {e}")
            return []
    
    def _parse_securities_only(self, securities: List) -> List[Dict[str, Any]]:
        result = []
        for security in securities[:200]:
            if not security or len(security) < 3:
                continue
            prev_price = float(security[6]) if len(security) > 6 and security[6] is not None else 0
            result.append({
                'ticker': security[0],
                'name': security[1],
                'full_name': security[2],
                'price': 0,
                'change': 0,
                'open_price': prev_price,
                'change_percent': 0,
                'volume': 0,
                'update_time': None,
                'isin': security[3] if len(security) > 3 else None,
                'regnumber': security[4] if len(security) > 4 else None,
                'lotsize': int(security[5]) if len(security) > 5 and security[5] else 1,
                'last_updated': datetime.now().isoformat(),
            })
        return result