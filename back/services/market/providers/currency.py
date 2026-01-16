import aiohttp
from datetime import datetime
from typing import List, Dict, Any
from back.contracts.market import IMarketDataProvider
from back.core.logger import logger


class CurrencyDataProvider(IMarketDataProvider):
    def __init__(self, moex_base_url: str):
        self.base_url = moex_base_url.rstrip("/")

    def get_cache_key(self) -> str:
        return "moex:currency"

    def get_asset_type(self) -> str:
        return "currency"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/engines/currency/markets/selt/securities.json"
            
            async with aiohttp.ClientSession() as session:
                securities_data = await self._fetch_securities(session, url)
                market_data = await self._fetch_market_data(session, url)
                return self._parse_currency_data(securities_data, market_data)
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching currencies: {e}")
            return []

    async def _fetch_securities(self, session: aiohttp.ClientSession, url: str) -> Dict:
        params = {
            'iss.meta': 'off',
            'securities.columns': 'SECID,SHORTNAME,SECNAME,PREVPRICE,PREVWAPRICE',
        }
        
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def _fetch_market_data(self, session: aiohttp.ClientSession, url: str) -> Dict:
        params = {
            'iss.meta': 'off',
            'iss.only': 'marketdata',
            'marketdata.columns': 'SECID,LAST,LASTCHANGE,LASTCHANGEPRC,OPEN,LOW,HIGH,VALUE',
        }
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            return {}

    def _parse_currency_data(self, securities_data: Dict, market_data: Dict) -> List[Dict[str, Any]]:
        securities = securities_data.get('securities', {}).get('data', [])
        securities_cols = securities_data.get('securities', {}).get('columns', [])
        
        marketdata = market_data.get('marketdata', {}).get('data', [])
        marketdata_cols = market_data.get('marketdata', {}).get('columns', [])
        
        secid_idx = securities_cols.index('SECID')
        shortname_idx = securities_cols.index('SHORTNAME')
        secname_idx = securities_cols.index('SECNAME')
        prevprice_idx = securities_cols.index('PREVPRICE')
        prevwaprice_idx = securities_cols.index('PREVWAPRICE')
        
        if marketdata_cols:
            market_secid_idx = marketdata_cols.index('SECID') if 'SECID' in marketdata_cols else -1
            last_idx = marketdata_cols.index('LAST') if 'LAST' in marketdata_cols else -1
            change_idx = marketdata_cols.index('LASTCHANGE') if 'LASTCHANGE' in marketdata_cols else -1
            pct_idx = marketdata_cols.index('LASTCHANGEPRC') if 'LASTCHANGEPRC' in marketdata_cols else -1
            open_idx = marketdata_cols.index('OPEN') if 'OPEN' in marketdata_cols else -1
            low_idx = marketdata_cols.index('LOW') if 'LOW' in marketdata_cols else -1
            high_idx = marketdata_cols.index('HIGH') if 'HIGH' in marketdata_cols else -1
        else:
            market_secid_idx = last_idx = change_idx = pct_idx = open_idx = low_idx = high_idx = -1
        
        market_dict = {}
        for item in marketdata:
            if item and market_secid_idx != -1 and len(item) > market_secid_idx:
                ticker = item[market_secid_idx]
                market_dict[ticker] = item
        
        result = []
        for security in securities:
            if not security:
                continue
                
            ticker = security[secid_idx]
            shortname = security[shortname_idx]
            secname = security[secname_idx]
            prevprice = security[prevprice_idx] if prevprice_idx < len(security) else None
            prevwaprice = security[prevwaprice_idx] if prevwaprice_idx < len(security) else None
            
            market_item = market_dict.get(ticker, [])
            
            price = None
            if last_idx != -1 and last_idx < len(market_item) and market_item[last_idx] is not None:
                price = market_item[last_idx]
            elif prevwaprice is not None:
                price = prevwaprice
            elif prevprice is not None:
                price = prevprice
            
            change = None
            if change_idx != -1 and change_idx < len(market_item) and market_item[change_idx] is not None:
                change = market_item[change_idx]
            
            change_percent = None
            if pct_idx != -1 and pct_idx < len(market_item) and market_item[pct_idx] is not None:
                change_percent = market_item[pct_idx]
            
            display_name = shortname if shortname else secname if secname else ticker
            
            if not self._is_main_currency(ticker, display_name):
                continue
            
            currency_data = {
                'ticker': ticker,
                'name': display_name,
                'full_name': secname if secname else display_name,
                'price': float(price) if price is not None else 0,
                'change': float(change) if change is not None else 0,
                'change_percent': float(change_percent) if change_percent is not None else 0,
                'last_updated': datetime.now().isoformat(),
                'asset_type': 'currency',
            }
            
            result.append(currency_data)
        
        logger.info(f"Parsed {len(result)} currencies")
        return result
    
    def _is_main_currency(self, ticker: str, name: str) -> bool:
        main_currencies = ['USD', 'EUR', 'CNY', 'GBP', 'JPY', 'CHF', 'TRY', 'HKD', 'KZT', 'BYN']
        
        for currency in main_currencies:
            if currency in ticker:
                return True
        
        for currency in main_currencies:
            if currency in name.upper():
                return True
        
        excluded = ['TODTOM', 'TOMSPT', 'SPT', 'FWD', 'LTV', 'TMS', 'TOD1D', 'TOM1D', 
                   'TOM1W', 'TOM2W', 'TOM1M', 'TOM2M', 'TOM3M', 'TOM6M', 'TOM9M', 'TOM1Y']
        
        for exclude in excluded:
            if exclude in ticker:
                return False
        
        return True
