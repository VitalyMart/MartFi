import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from back.contracts.market import IMarketDataProvider
from back.core.logger import logger

class BondsDataProvider(IMarketDataProvider):
    def __init__(self, moex_base_url: str):
        self.moex_base_url = moex_base_url.rstrip('/')
        self.NOMINAL = 1000  # Номинал облигации в рублях
        # Все доски облигаций на Московской бирже
        self.bond_boards = ['TQOB', 'TQCB', 'TQDB', 'TQRB', 'TQPB', 'TQNB']

    def get_cache_key(self) -> str:
        return "moex:bonds"

    def get_asset_type(self) -> str:
        return "bond"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        try:
            securities_data = await self._fetch_securities_data()
            if not securities_data:
                return []
            
            market_data = await self._fetch_market_data_all_boards()
            
            return self._merge_data(securities_data, market_data)
            
        except Exception as e:
            logger.error(f"Error fetching bonds: {e}")
            return []

    async def _fetch_securities_data(self) -> Dict[str, Dict[str, Any]]:
        url = f"{self.moex_base_url}/engines/stock/markets/bonds/securities.json"
        params = {
            'iss.meta': 'off',
            'securities.columns': 'SECID,SHORTNAME,SECNAME,ISIN,MATDATE,COUPONVALUE,COUPONPERIOD,NEXTCOUPON,CURRENCYID,PREVPRICE,PREVWAPRICE,LOTSIZE,ISSUESIZE'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"MOEX securities API error: {response.status}")
                        return {}
                    
                    data = await response.json()
                    securities = data.get('securities', {})
                    columns = securities.get('columns', [])
                    rows = securities.get('data', [])
                    
                    return self._parse_securities(columns, rows)
        except Exception as e:
            logger.error(f"Error fetching securities: {e}")
            return {}

    async def _fetch_market_data_all_boards(self) -> Dict[str, Dict[str, Any]]:
        """Собирает рыночные данные со всех досок облигаций"""
        all_market_data = {}
        
        async with aiohttp.ClientSession() as session:
            for board in self.bond_boards:
                try:
                    board_data = await self._fetch_board_market_data(session, board)
                    # Объединяем данные, приоритет у TQOB (ОФЗ) если есть дубликаты
                    for ticker, data in board_data.items():
                        if ticker not in all_market_data or board == 'TQOB':
                            all_market_data[ticker] = data
                except Exception as e:
                    logger.warning(f"Error fetching market data for board {board}: {e}")
                    continue
        
        logger.info(f"Fetched market data for {len(all_market_data)} bonds from all boards")
        return all_market_data

    async def _fetch_board_market_data(self, session: aiohttp.ClientSession, board: str) -> Dict[str, Dict[str, Any]]:
        """Собирает рыночные данные с конкретной доски"""
        url = f"{self.moex_base_url}/engines/stock/markets/bonds/boards/{board}/securities.json"
        params = {
            'iss.meta': 'off',
            'iss.only': 'marketdata',
            'marketdata.columns': 'SECID,LAST,LASTTOPREVPRICE,CHANGE,YIELD,OPEN,HIGH,LOW,VALUE,UPDATETIME'
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.debug(f"MOEX {board} marketdata error: {response.status}")
                    return {}
                
                data = await response.json()
                marketdata = data.get('marketdata', {})
                columns = marketdata.get('columns', [])
                rows = marketdata.get('data', [])
                
                return self._parse_market_data(columns, rows, board)
        except Exception as e:
            logger.debug(f"Error fetching {board} market data: {e}")
            return {}

    def _parse_securities(self, columns: List[str], rows: List[List]) -> Dict[str, Dict[str, Any]]:
        result = {}
        col_index = {col: idx for idx, col in enumerate(columns)}
        
        for row in rows:
            if not row:
                continue
            
            ticker = row[col_index.get('SECID', 0)]
            
            result[ticker] = {
                'short_name': self._safe_str(row, col_index.get('SHORTNAME'), ticker),
                'sec_name': self._safe_str(row, col_index.get('SECNAME'), ''),
                'isin': self._safe_str(row, col_index.get('ISIN')),
                'maturity_date': self._safe_str(row, col_index.get('MATDATE')),
                'coupon_value': self._safe_float(row, col_index.get('COUPONVALUE'), 0.0),
                'coupon_period': self._safe_int(row, col_index.get('COUPONPERIOD'), 0),
                'next_coupon': self._safe_str(row, col_index.get('NEXTCOUPON')),
                'currency': self._safe_str(row, col_index.get('CURRENCYID'), 'RUB'),
                'prev_price': self._safe_float(row, col_index.get('PREVWAPRICE')) or 
                             self._safe_float(row, col_index.get('PREVPRICE')),
                'lotsize': self._safe_int(row, col_index.get('LOTSIZE'), 1),
                'issue_size': self._safe_float(row, col_index.get('ISSUESIZE'), 0.0),
            }
        
        logger.info(f"Parsed {len(result)} securities")
        return result

    def _parse_market_data(self, columns: List[str], rows: List[List], board: str = "") -> Dict[str, Dict[str, Any]]:
        result = {}
        col_index = {col: idx for idx, col in enumerate(columns)}
        
        for row in rows:
            if not row or len(row) < 10:
                continue
            
            ticker = row[col_index.get('SECID', 0)]
            
            last = self._safe_float(row, col_index.get('LAST'))
            if last == 0:
                continue
            
            change_rub = self._safe_float(row, col_index.get('LASTTOPREVPRICE'), 0.0)
            
            change_percent = 0.0
            if change_rub != 0:
                # Расчет процента изменения на основе цены в рублях
                price_rub = last * 10
                prev_price_rub = price_rub - change_rub
                if prev_price_rub > 0:
                    change_percent = (change_rub / prev_price_rub) * 100
            else:
                # Если нет изменения в рублях, используем CHANGE если он есть
                change_percent = self._safe_float(row, col_index.get('CHANGE'), 0.0)
            
            result[ticker] = {
                'price': last,
                'price_rub': round(last * 10, 2),  # Цена в рублях
                'change_percent': round(change_percent, 3),
                'yield': self._safe_float(row, col_index.get('YIELD'), 0.0),
                'open': self._safe_float(row, col_index.get('OPEN'), 0.0),
                'high': self._safe_float(row, col_index.get('HIGH'), 0.0),
                'low': self._safe_float(row, col_index.get('LOW'), 0.0),
                'volume': self._safe_float(row, col_index.get('VALUE'), 0.0),
                'update_time': self._safe_str(row, col_index.get('UPDATETIME')),
                'board': board,  # Сохраняем информацию о доске
            }
        
        logger.debug(f"Parsed {len(result)} market data entries from board {board}")
        return result

    def _merge_data(self, securities: Dict[str, Dict[str, Any]], market: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        
        for ticker, sec in securities.items():
            mkt = market.get(ticker)
            
            # Пропускаем облигации без рыночных данных
            if not mkt:
                continue
            
            # Проверяем, что цена валидная
            if mkt['price'] <= 0:
                continue
            
            result.append({
                'ticker': ticker,
                'name': sec['short_name'],
                'full_name': sec['sec_name'],
                'price': mkt['price'],
                'price_rub': mkt['price_rub'],  # Цена в рублях
                'nominal': self.NOMINAL,  # Номинал 1000₽
                'change_percent': mkt['change_percent'],
                'open_price': mkt['open'],
                'high': mkt['high'],
                'low': mkt['low'],
                'volume': mkt['volume'],
                'update_time': mkt['update_time'],
                'yield': mkt['yield'],
                'isin': sec['isin'],
                'lotsize': sec['lotsize'],
                'maturity_date': sec['maturity_date'],
                'coupon_value': sec['coupon_value'],
                'coupon_period': sec['coupon_period'],
                'next_coupon': sec['next_coupon'],
                'issue_size': sec['issue_size'],
                'currency': sec['currency'],
                'prev_price': sec['prev_price'],
                'last_updated': datetime.now().isoformat(),
                'asset_type': 'bond',
                'board': mkt.get('board', ''),  # Информация о торговой доске
            })
        
        logger.info(f"Fetched {len(result)} bonds from all boards")
        return result

    @staticmethod
    def _safe_float(row: List, index: Optional[int], default: float = 0.0) -> float:
        if index is None or index >= len(row):
            return default
        try:
            return float(row[index]) if row[index] is not None else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int(row: List, index: Optional[int], default: int = 0) -> int:
        if index is None or index >= len(row):
            return default
        try:
            return int(row[index]) if row[index] is not None else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_str(row: List, index: Optional[int], default: str = '') -> str:
        if index is None or index >= len(row):
            return default
        return str(row[index]) if row[index] is not None else default