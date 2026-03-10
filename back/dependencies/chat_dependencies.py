from fastapi import Depends
from ..services.openrouter_service import OpenRouterService
from ..services.rag_service import RAGService
from ..services.chat_service import ChatService

# Создаем синглтоны на уровне модуля
_rag_service = None
_openrouter_service = None

def get_openrouter_service() -> OpenRouterService:
    global _openrouter_service
    if _openrouter_service is None:
        _openrouter_service = OpenRouterService()
    return _openrouter_service

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

def get_chat_service(
    openrouter_service: OpenRouterService = Depends(get_openrouter_service),
    rag_service: RAGService = Depends(get_rag_service)
) -> ChatService:
    return ChatService(openrouter_service, rag_service)