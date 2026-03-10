from fastapi import Depends
from ..services.openrouter_service import OpenRouterService
from ..services.rag_service import RAGService
from ..services.chat_service import ChatService

def get_openrouter_service() -> OpenRouterService:
    return OpenRouterService()

def get_rag_service() -> RAGService:
    return RAGService()

def get_chat_service(
    openrouter_service: OpenRouterService = Depends(get_openrouter_service),
    rag_service: RAGService = Depends(get_rag_service)
) -> ChatService:
    return ChatService(openrouter_service, rag_service)