import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from ..core.logger import logger
from ..core.redis_client import redis_client
from .openrouter_service import OpenRouterService
from .rag_service import RAGService

class ChatService:
    def __init__(self, openrouter_service: OpenRouterService, rag_service: RAGService):
        self.openrouter = openrouter_service
        self.rag = rag_service
        self.history_ttl = 86400

    async def process_message(self, message: str, user_id: Optional[int] = None, session_id: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        history = await self._get_chat_history(user_id, session_id)
        rag_context = await self.rag.get_rag_response(message, user_id)

        messages = self._build_messages(history, message, rag_context)
        start_time = datetime.now()

        response = await self.openrouter.chat_completion(
            messages=messages,
            model=model,
            temperature=0.7,
            max_tokens=1500
        )

        response_time = (datetime.now() - start_time).total_seconds()
        assistant_message = self._extract_response(response)

        await self._save_to_history(
            user_id=user_id,
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message,
            metadata={
                "rag_context_used": rag_context.get("context_used") if rag_context else False,
                "documents_used": rag_context.get("documents_used") if rag_context else [],
                "model": model or self.openrouter.default_model,
                "response_time": response_time
            }
        )

        return {
            "success": True,
            "message": assistant_message,
            "rag_used": rag_context and rag_context.get("context_used"),
            "documents_used": rag_context.get("documents_used") if rag_context else [],
            "response_time": response_time,
            "model": model or self.openrouter.default_model
        }

    async def process_message_stream(self, message: str, user_id: Optional[int] = None, session_id: Optional[str] = None, model: Optional[str] = None) -> AsyncGenerator[str, None]:
        history = await self._get_chat_history(user_id, session_id)
        rag_context = await self.rag.get_rag_response(message, user_id)

        messages = self._build_messages(history, message, rag_context)
        full_response = ""

        async for chunk in self.openrouter.chat_completion_stream(
            messages=messages,
            model=model,
            temperature=0.7,
            max_tokens=1500
        ):
            yield chunk
            if chunk.startswith('data: ') and chunk != 'data: [DONE]\n':
                try:
                    data = json.loads(chunk[6:])
                    if 'choices' in data and len(data['choices']) > 0:
                        delta = data['choices'][0].get('delta', {})
                        if 'content' in delta:
                            full_response += delta['content']
                except:
                    pass

        if full_response:
            await self._save_to_history(
                user_id=user_id,
                session_id=session_id,
                user_message=message,
                assistant_message=full_response,
                metadata={
                    "rag_context_used": rag_context.get("context_used") if rag_context else False,
                    "documents_used": rag_context.get("documents_used") if rag_context else [],
                    "model": model or self.openrouter.default_model,
                    "streamed": True
                }
            )

    def _build_messages(self, history: List[Dict[str, str]], current_message: str, rag_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        system_prompt = """Ты - финансовый ассистент MartFi, помогающий пользователям с инвестициями на российском рынке.
Ты отвечаешь на русском языке, дружелюбно и профессионально.
Твои ответы должны быть точными, полезными и основанными на фактах.

ВАЖНОЕ ПРАВИЛО ДЛЯ ТАБЛИЦ:
    Не используй markdown для таблиц
    Не нужно их оборачивать во что либо 
    Используй сухой html

Пример правильного вывода таблицы:
<table>
<tr><th>Заголовок 1</th><th>Заголовок 2</th></tr>
<tr><td>Данные 1</td><td>Данные 2</td></tr>
</table>
"""
        
        if rag_context and rag_context.get("context_used"):
            documents = rag_context.get("documents_used", [])
            doc_names = [self.rag._get_doc_display_name(doc) for doc in documents]
            system_prompt += f"\n\nДля ответа на этот вопрос я использую информацию из документов: {', '.join(doc_names)}."
            if rag_context.get("context"):
                system_prompt += f"\n\nКонтекст:\n{rag_context['context']}"
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:
            messages.append(msg)
        messages.append({"role": "user", "content": current_message})
        return messages

    def _extract_response(self, response: Dict[str, Any]) -> str:
        try:
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            elif "error" in response:
                return f"Ошибка: {response['error']}"
            else:
                return "Не удалось получить ответ от ассистента"
        except Exception as e:
            logger.error(f"Error extracting response: {e}")
            return "Ошибка при обработке ответа"

    async def _get_chat_history(self, user_id: Optional[int], session_id: Optional[str]) -> List[Dict[str, str]]:
        if not user_id and not session_id:
            return []
        key = f"chat_history:{user_id or session_id}"
        try:
            history = await redis_client.get(key)
            if history:
                return json.loads(history)
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
        return []

    async def _save_to_history(self, user_id: Optional[int], session_id: Optional[str], user_message: str, assistant_message: str, metadata: Dict[str, Any]):
        if not user_id and not session_id:
            return
        key = f"chat_history:{user_id or session_id}"
        try:
            history = await self._get_chat_history(user_id, session_id)
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": assistant_message})
            if len(history) > 50:
                history = history[-50:]
            await redis_client.setex(key, self.history_ttl, json.dumps(history))
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")

    async def clear_history(self, user_id: Optional[int], session_id: Optional[str]) -> bool:
        if not user_id and not session_id:
            return False
        key = f"chat_history:{user_id or session_id}"
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return False