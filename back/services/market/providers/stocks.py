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
                    'securities.columns': 'SECID,SHORTNAME,SECNAME,ISIN,REGNUMBER,LOTSIZE',
                }
                async with session.get(url, params=securities_params) as response:
                    if response.status != 200:
                        logger.error(f"MOEX API error: {response.status}")
                        return []
                    data = await response.json()
                    securities = data.get('securities', {}).get('data', [])

                marketdata_params = {
                    'iss.meta': 'off',
                    'marketdata.columns': 'SECID,LAST,LASTTOPREVPRICE,OPEN,CHANGE,VALUE,UPDATETIME',
                }
                marketdata_url = url + "?iss.only=marketdata"
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
                            'update_time': item[6] if len(item) > 6 else None,
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
                    market_info = market_dict.get(
                        ticker,
                        {'price': 0, 'change': 0, 'open': 0, 'change_percent': 0, 'volume': 0, 'update_time': None},
                    )
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
                        'last_updated': datetime.now().isoformat(),
                    })
                logger.info(f"Fetched {len(result)} stocks from MOEX")
                return result

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
                'last_updated': datetime.now().isoformat(),
            })
        return result