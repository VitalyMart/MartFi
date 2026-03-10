import aiohttp
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from ..core.logger import logger
from ..config_openrouter import openrouter_settings
from ..core.redis_client import redis_client

class OpenRouterService:
    def __init__(self):
        self.api_key = openrouter_settings.API_KEY
        self.base_url = openrouter_settings.BASE_URL
        self.default_model = openrouter_settings.DEFAULT_MODEL
        self.cache_ttl = 3600

    async def chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000, stream: bool = False) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "API key not configured", "choices": [{"message": {"content": "Сервис AI временно недоступен"}}]}

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": openrouter_settings.SITE_URL,
            "X-Title": openrouter_settings.SITE_NAME
        }
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                        return {"error": f"API error: {response.status}", "choices": [{"message": {"content": f"Ошибка AI сервиса. Код: {response.status}"}}]}
                    return await response.json()
        except Exception as e:
            logger.error(f"Error calling OpenRouter: {e}")
            return {"error": str(e), "choices": [{"message": {"content": "Внутренняя ошибка сервера"}}]}

    async def chat_completion_stream(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield f"data: {json.dumps({'error': 'API key not configured'})}\n"
            return

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": openrouter_settings.SITE_URL,
            "X-Title": openrouter_settings.SITE_NAME
        }
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenRouter stream error: {response.status} - {error_text}")
                        yield f"data: {json.dumps({'error': f'API error: {response.status}'})}\n"
                        return
                    async for line in response.content:
                        if line:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                yield line + '\n'
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n"