import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any
from back.contracts.market import IMarketDataProvider
from back.core.logger import logger

class BondsDataProvider(IMarketDataProvider):
    def __init__(self, moex_base_url: str):
        self.moex_base_url = moex_base_url.rstrip()
        self.bond_boards = ['TQOB', 'TQCB', 'TQDB', 'TQRB', 'TQPB', 'TQNB']

    def get_cache_key(self) -> str:
        return "moex:bonds:all"

    def get_asset_type(self) -> str:
        return "bond"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.moex_base_url}/engines/stock/markets/bonds/securities.json"
            
            async with aiohttp.ClientSession() as session:
                securities_params = {
                    'iss.meta': 'off',
                    'securities.columns': 'SECID,SHORTNAME,SECNAME,ISIN,REGNUMBER,LOTSIZE,MATDATE,COUPONVALUE,COUPONPERIOD,NEXTCOUPON,ISSUESIZE,CURRENCYID,PREVPRICE,PREVWAPRICE',
                }
                
                async with session.get(url, params=securities_params) as response:
                    if response.status != 200:
                        logger.error(f"MOEX Bonds API error: {response.status}")
                        return []
                    
                    data = await response.json()
                    all_securities = data.get('securities', {}).get('data', [])
                    securities_columns = data.get('securities', {}).get('columns', [])
                
                prevprice_idx = securities_columns.index('PREVPRICE') if 'PREVPRICE' in securities_columns else -1
                prevwaprice_idx = securities_columns.index('PREVWAPRICE') if 'PREVWAPRICE' in securities_columns else -1
                
                market_data_dict = {}
                
                for board in self.bond_boards:
                    try:
                        market_url = f"{self.moex_base_url}/engines/stock/markets/bonds/boards/{board}/securities.json"
                        market_params = {
                            'iss.meta': 'off',
                            'marketdata.columns': 'SECID,LAST,LASTTOPREVPRICE,OPEN,CHANGE,VALUE,UPDATETIME,YIELD',
                        }
                        marketdata_url = market_url + "?iss.only=marketdata"
                        
                        async with session.get(marketdata_url, params=market_params) as response:
                            if response.status == 200:
                                marketdata = await response.json()
                                market_data_list = marketdata.get('marketdata', {}).get('data', [])
                                
                                for item in market_data_list:
                                    if item and len(item) >= 8:
                                        ticker = item[0]
                                        if ticker not in market_data_dict:
                                            market_data_dict[ticker] = {
                                                'price': float(item[1]) if item[1] is not None else 0,
                                                'change': float(item[2]) if item[2] is not None else 0,
                                                'open': float(item[3]) if item[3] is not None else 0,
                                                'change_percent': float(item[4]) if item[4] is not None else 0,
                                                'volume': float(item[5]) if item[5] is not None else 0,
                                                'update_time': item[6] if len(item) > 6 else None,
                                                'yield': float(item[7]) if len(item) > 7 and item[7] is not None else 0,
                                            }
                    except Exception as e:
                        logger.warning(f"Error fetching market data for board {board}: {e}")
                        continue

                result = []
                for security in all_securities[:1000]:
                    if not security or len(security) < 12:
                        continue
                    
                    ticker = security[0]
                    name = security[1]
                    full_name = security[2]
                    isin = security[3] if len(security) > 3 else None
                    regnumber = security[4] if len(security) > 4 else None
                    lotsize = int(security[5]) if len(security) > 5 and security[5] else 1
                    maturity_date = security[6] if len(security) > 6 else None
                    coupon_value = float(security[7]) if len(security) > 7 and security[7] is not None else 0
                    coupon_period = int(security[8]) if len(security) > 8 and security[8] is not None else 0
                    next_coupon = security[9] if len(security) > 9 else None
                    issue_size = float(security[10]) if len(security) > 10 and security[10] is not None else 0
                    currency = security[11] if len(security) > 11 else "RUB"

                    market_info = market_data_dict.get(
                        ticker,
                        {
                            'price': 0, 
                            'change': 0, 
                            'open': 0, 
                            'change_percent': 0, 
                            'volume': 0, 
                            'update_time': None,
                            'yield': 0
                        },
                    )

                    price = market_info['price']
                    
                    if price == 0:
                        if prevwaprice_idx != -1 and prevwaprice_idx < len(security) and security[prevwaprice_idx] is not None:
                            price = security[prevwaprice_idx]
                        elif prevprice_idx != -1 and prevprice_idx < len(security) and security[prevprice_idx] is not None:
                            price = security[prevprice_idx]

                    if price == 0:
                        continue

                    result.append({
                        'ticker': ticker,
                        'name': name,
                        'full_name': full_name,
                        'price': float(price) if price is not None else 0,
                        'change': market_info['change'],
                        'open_price': market_info['open'],
                        'change_percent': market_info['change_percent'],
                        'volume': market_info['volume'],
                        'update_time': market_info['update_time'],
                        'isin': isin,
                        'regnumber': regnumber,
                        'lotsize': lotsize,
                        'maturity_date': maturity_date,
                        'coupon_value': coupon_value,
                        'coupon_period': coupon_period,
                        'next_coupon': next_coupon,
                        'issue_size': issue_size,
                        'currency': currency,
                        'yield': market_info['yield'],
                        'last_updated': datetime.now().isoformat(),
                        'asset_type': 'bond',
                    })
                
                logger.info(f"Fetched {len(result)} bonds from MOEX")
                return result

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching MOEX bonds data: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching bonds: {e}")
            return []

    def _parse_securities_only(self, securities: List) -> List[Dict[str, Any]]:
        result = []
        for security in securities[:500]:
            if not security or len(security) < 12:
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
                'maturity_date': security[6] if len(security) > 6 else None,
                'coupon_value': float(security[7]) if len(security) > 7 and security[7] is not None else 0,
                'coupon_period': int(security[8]) if len(security) > 8 and security[8] is not None else 0,
                'next_coupon': security[9] if len(security) > 9 else None,
                'issue_size': float(security[10]) if len(security) > 10 and security[10] is not None else 0,
                'currency': security[11] if len(security) > 11 else "RUB",
                'yield': 0,
                'last_updated': datetime.now().isoformat(),
                'asset_type': 'bond',
            })
        return result