import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import asyncio
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from qdrant_client import AsyncQdrantClient
from ..core.logger import logger
from ..core.redis_client import redis_client
from ..config_qdrant import qdrant_settings
from dotenv import load_dotenv

load_dotenv()

class RAGService:
    _instance = None
    _embeddings = None
    _async_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            logger.info("Initializing RAG service (singleton)")
            self.hf_token = os.getenv("TOKEN_HUGGINGFACE")
            if not self.hf_token:
                logger.warning("TOKEN_HUGGINGFACE not found in .env")
            self._init_embeddings()
            self._init_qdrant()
            self.cache_ttl = 3600
            self.top_k = 5
            self.initialized = True
            logger.info("RAG service initialized successfully")

    def _init_embeddings(self):
        if RAGService._embeddings is None:
            logger.info(f"Loading embedding model: {qdrant_settings.EMBEDDING_MODEL}")
            model_kwargs = {"device": "cpu"}
            if self.hf_token:
                model_kwargs["token"] = self.hf_token
            RAGService._embeddings = HuggingFaceEmbeddings(
                model_name=qdrant_settings.EMBEDDING_MODEL,
                model_kwargs=model_kwargs,
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Embedding model loaded")
        self.embeddings = RAGService._embeddings

    def _init_qdrant(self):
        if RAGService._async_client is None:
            logger.info(f"Connecting to Qdrant: {qdrant_settings.QDRANT_HOST}:{qdrant_settings.QDRANT_PORT}")
            RAGService._async_client = AsyncQdrantClient(
                host=qdrant_settings.QDRANT_HOST,
                port=qdrant_settings.QDRANT_PORT,
            )
            logger.info("Async Qdrant client created")
        self.async_client = RAGService._async_client

    async def search_relevant_chunks(self, query: str, top_k: int = None) -> List[Document]:
        try:
            k = top_k or self.top_k
            loop = asyncio.get_event_loop()
            query_vector = await loop.run_in_executor(None, self.embeddings.embed_query, query)
            
            results = await self.async_client.query_points(
                collection_name=qdrant_settings.COLLECTION_NAME,
                query=query_vector,
                limit=k,
                with_payload=True,
                with_vectors=False
            )
            
            documents = []
            for point in results.points:
                if point.payload:
                    doc = Document(
                        page_content=point.payload.get("page_content", ""),
                        metadata={
                            "source": point.payload.get("metadata", {}).get("source", ""),
                            "summary": point.payload.get("metadata", {}).get("summary", ""),
                            "keywords": point.payload.get("metadata", {}).get("keywords", ""),
                            "questions": point.payload.get("metadata", {}).get("questions", ""),
                        }
                    )
                    documents.append(doc)
            
            logger.info(f"Found {len(documents)} relevant chunks for query")
            return documents
        except Exception as e:
            logger.error(f"Error searching chunks: {e}", exc_info=True)
            return []

    def build_context(self, documents: List[Document]) -> str:
        if not documents:
            return ""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get('source', 'Unknown')
            doc_display_name = self._get_doc_display_name(source)
            context_parts.append(f"[Документ {i}: {doc_display_name}]\n{doc.page_content}\n")
        return "\n---\n".join(context_parts)

    def _get_doc_display_name(self, doc_name: str) -> str:
        display_names = {
            'bonds_guide': 'Руководство по облигациям',
            'companies': 'Информация о компаниях',
            'funds_guide': 'Руководство по фондам',
            'index': 'Индексы',
            'stocks_guide': 'Руководство по акциям',
            'about_MartFi': 'О MartFi'
        }
        return display_names.get(doc_name, doc_name)

    async def get_rag_response(self, query: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        cache_key = f"rag_response:{hashlib.md5(query.encode()).hexdigest()}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis cache error: {e}")

        relevant_docs = await self.search_relevant_chunks(query)
        context = self.build_context(relevant_docs)
        documents_used = list(set([doc.metadata.get('source', 'Unknown') for doc in relevant_docs]))

        result = {
            "query": query,
            "context_used": bool(context),
            "chunks_count": len(relevant_docs),
            "documents_used": documents_used,
            "context": context
        }

        try:
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")

        return result