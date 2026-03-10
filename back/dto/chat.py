from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    model: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    message: str
    rag_used: bool = False
    documents_used: List[str] = []
    response_time: Optional[float] = None
    model: Optional[str] = None

class RAGDocumentInfo(BaseModel):
    name: str
    display_name: str
    size: int
    chunks: int