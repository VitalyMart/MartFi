# FILE: ./back/services/market/providers/cbr_rates.py
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import Dict, Optional
from back.core.logger import logger


class CBRRateProvider:
    def __init__(self):
        self.base_url = "https://www.cbr.ru/scripts/XML_daily.asp"

    async def fetch_rates(self, target_date: Optional[date] = None) -> Dict[str, float]:
        try:
            params = {}
            if target_date:
                params['date_req'] = target_date.strftime('%d/%m/%Y')

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"CBR API error: {response.status}")
                        return {}

                    text_data = await response.text()
                    return self._parse_xml(text_data)

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching CBR rates: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching CBR rates: {e}")
            return {}

    def _parse_xml(self, xml_data: str) -> Dict[str, float]:
        result = {}
        try:
            root = ET.fromstring(xml_data)
            for valute in root.findall('Valute'):
                char_code = valute.find('CharCode').text
                value = valute.find('Value').text.replace(',', '.')
                nominal = float(valute.find('Nominal').text.replace(',', '.'))
                rate = float(value) / nominal
                result[char_code] = rate
            logger.info(f"Parsed {len(result)} currency rates from CBR")
            return result
        except Exception as e:
            logger.error(f"Error parsing CBR XML: {e}")
            return {}