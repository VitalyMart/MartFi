import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any
from back.contracts.market import IMarketDataProvider
from back.core.logger import logger

class IndicesDataProvider(IMarketDataProvider):
    def __init__(self, moex_base_url: str):
        self.moex_base_url = moex_base_url.rstrip()

    def get_cache_key(self) -> str:
        return "moex:indices"

    def get_asset_type(self) -> str:
        return "indices"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.moex_base_url}/engines/stock/markets/index/boards/SNDX/securities.json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={'iss.meta': 'off'}) as response:
                    if response.status != 200:
                        logger.error(f"MOEX API error: {response.status}")
                        return []
                    
                    text_data = await response.text()
                    
                    if not text_data or len(text_data) < 100:
                        logger.error("API returned empty or very short response")
                        return []
                    
                    try:
                        data = json.loads(text_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        return []
                    
                    if 'securities' not in data:
                        logger.error("No 'securities' section in response")
                        return []
                    
                    securities_data = data.get('securities', {}).get('data', [])
                    securities_columns = data.get('securities', {}).get('columns', [])
                    
                    marketdata_data = data.get('marketdata', {}).get('data', [])
                    marketdata_columns = data.get('marketdata', {}).get('columns', [])
                    
                    if not securities_data:
                        logger.warning("No securities data found in API response")
                        return []
                    
                    result = self._parse_data(securities_data, securities_columns, 
                                            marketdata_data, marketdata_columns)
                    
                    logger.info(f"Successfully parsed {len(result)} indices")
                    return result
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []
    
    def _parse_data(self, securities_data, securities_columns, marketdata_data, marketdata_columns):
        result = []
        
        market_dict = {}
        for market_item in marketdata_data:
            if market_item and len(market_item) > 0:
                try:
                    if 'SECID' in marketdata_columns:
                        secid_idx = marketdata_columns.index('SECID')
                        ticker = market_item[secid_idx]
                        market_dict[ticker] = market_item
                except (ValueError, IndexError):
                    continue
        
        for security in securities_data:
            if not security or len(security) < 3:
                continue
            
            try:
                secid_idx = securities_columns.index('SECID') if 'SECID' in securities_columns else 0
                ticker = security[secid_idx]
                
                name = ""
                for name_field in ['SHORTNAME', 'NAME', 'SECNAME']:
                    if name_field in securities_columns:
                        name_idx = securities_columns.index(name_field)
                        if security[name_idx]:
                            name = security[name_idx]
                            break
                
                full_name = ""
                for full_name_field in ['NAME', 'SECNAME', 'SHORTNAME']:
                    if full_name_field in securities_columns:
                        full_idx = securities_columns.index(full_name_field)
                        if security[full_idx] and security[full_idx] != name:
                            full_name = security[full_idx]
                            break
                
                if not full_name:
                    full_name = name
                
                currency = "RUB"
                if 'CURRENCYID' in securities_columns:
                    curr_idx = securities_columns.index('CURRENCYID')
                    if security[curr_idx]:
                        currency = security[curr_idx]
                
                price = 0
                change = 0
                change_percent = 0
                open_price = 0
                high = 0
                low = 0
                
                market_item = market_dict.get(ticker)
                if market_item:
                    for price_field in ['CURRENTVALUE', 'LASTVALUE', 'LAST', 'VALUE']:
                        if price_field in marketdata_columns:
                            price_idx = marketdata_columns.index(price_field)
                            if market_item[price_idx] is not None:
                                try:
                                    price = float(market_item[price_idx])
                                    break
                                except (ValueError, TypeError):
                                    continue
                    
                    for change_field in ['LASTCHANGE', 'CHANGE']:
                        if change_field in marketdata_columns:
                            change_idx = marketdata_columns.index(change_field)
                            if market_item[change_idx] is not None:
                                try:
                                    change = float(market_item[change_idx])
                                    break
                                except (ValueError, TypeError):
                                    continue
                    
                    for pct_field in ['LASTCHANGEPRC', 'CHANGEPRC']:
                        if pct_field in marketdata_columns:
                            pct_idx = marketdata_columns.index(pct_field)
                            if market_item[pct_idx] is not None:
                                try:
                                    change_percent = float(market_item[pct_idx])
                                    break
                                except (ValueError, TypeError):
                                    continue
                    
                    for open_field in ['OPENVALUE', 'OPEN']:
                        if open_field in marketdata_columns:
                            open_idx = marketdata_columns.index(open_field)
                            if market_item[open_idx] is not None:
                                try:
                                    open_price = float(market_item[open_idx])
                                    break
                                except (ValueError, TypeError):
                                    continue
                    
                    for high_field in ['HIGH', 'HIGHVALUE']:
                        if high_field in marketdata_columns:
                            high_idx = marketdata_columns.index(high_field)
                            if market_item[high_idx] is not None:
                                try:
                                    high = float(market_item[high_idx])
                                    break
                                except (ValueError, TypeError):
                                    continue
                    
                    for low_field in ['LOW', 'LOWVALUE']:
                        if low_field in marketdata_columns:
                            low_idx = marketdata_columns.index(low_field)
                            if market_item[low_idx] is not None:
                                try:
                                    low = float(market_item[low_idx])
                                    break
                                except (ValueError, TypeError):
                                    continue
                
                index_data = {
                    'ticker': ticker,
                    'name': name,
                    'full_name': full_name,
                    'price': price,
                    'change': change,
                    'open_price': open_price,
                    'change_percent': change_percent,
                    'volume': 0,
                    'update_time': datetime.now().strftime("%H:%M:%S"),
                    'high': high,
                    'low': low,
                    'close': 0,
                    'currency': currency,
                    'last_updated': datetime.now().isoformat(),
                    'asset_type': 'index',
                }
                
                result.append(index_data)
                
            except Exception as e:
                logger.warning(f"Error parsing security {security[0] if security else 'unknown'}: {e}")
                continue
        
        return result