# services/rag_service.py
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

    _TICKER_MAP = {
        "сбербанк": "SBER",
        "сбер": "SBER",
        "sber": "SBER",
        "втб": "VTBR",
        "vtbr": "VTBR",
        "газпром": "GAZP",
        "gazp": "GAZP",
        "лукойл": "LKOH",
        "lukoil": "LKOH",
        "новатэк": "NVTK",
        "novatek": "NVTK",
        "nvtk": "NVTK",
        "озон": "OZON",
        "ozon": "OZON",
        "полюс": "PLZL",
        "plzl": "PLZL",
        "x5": "X5",
        "x5 group": "X5",
        "яндекс": "YDEX",
        "yandex": "YDEX",
        "ydex": "YDEX",
        "татнефть": "TATN",
        "tatn": "TATN",
        "сургутнефтегаз": "SNGS",
        "sngs": "SNGS",
        "норильский никель": "GMKN",
        "норникель": "GMKN",
        "gmkn": "GMKN",
        "московская биржа": "MOEX",
        "moex": "MOEX",
        "т-технологии": "T",
        "т банк": "T",
        "tcsg": "T",
        "роснефть": "ROSN",
        "rosn": "ROSN",
    }

    @classmethod
    def extract_ticker_from_query(cls, query: str) -> Optional[str]:
        if not query:
            return None
        query_lower = query.lower()
        for key, ticker in cls._TICKER_MAP.items():
            if key in query_lower:
                return ticker
        return None

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
            self.normal_top_k = 3
            self.reporting_top_k = 5
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

    async def search_relevant_chunks(self, query: str, top_k: Optional[int] = None, reporting_mode: bool = False) -> List[Document]:
        try:
            k = top_k or self.normal_top_k
            logger.info(f"Searching for query: '{query[:50]}...' with top_k={k}, reporting_mode={reporting_mode}")

            loop = asyncio.get_event_loop()
            query_vector = await loop.run_in_executor(None, self.embeddings.embed_query, query)

            all_documents = []

            target_ticker = None
            if reporting_mode:
                target_ticker = self.extract_ticker_from_query(query)
                if target_ticker:
                    logger.info(f"Filtering by ticker: {target_ticker}")

            for collection_name in qdrant_settings.ALL_COLLECTIONS:
                try:
                    query_filter = None
                    if reporting_mode and target_ticker:
                        query_filter = {
                            "must": [
                                {
                                    "key": "metadata.ticker",
                                    "match": {"value": target_ticker}
                                }
                            ]
                        }

                    results = await self.async_client.query_points(
                        collection_name=collection_name,
                        query=query_vector,
                        query_filter=query_filter,
                        limit=k,
                        with_payload=True,
                        with_vectors=False
                    )

                    logger.info(f"Found {len(results.points)} points in {collection_name}")
                    for idx, point in enumerate(results.points):
                        if point.payload:
                            payload = point.payload

                            if 'metadata' in payload:
                                meta = payload['metadata']
                                company = meta.get('company', 'Unknown')
                                ticker = meta.get('ticker', '')
                                content = payload.get('page_content', '')
                                source = meta.get('source', '')
                                summary = meta.get('summary', '')
                                keywords = meta.get('keywords', [])
                                questions = meta.get('questions', [])
                                period = meta.get('period', '')
                                quarter = meta.get('quarter', '')
                                report_type = meta.get('report_type', '')
                                report_date = meta.get('report_date', '')
                                currency = meta.get('currency', '')
                            else:
                                company = payload.get('company', 'Unknown')
                                ticker = payload.get('ticker', '')
                                content = payload.get('page_content', '')
                                source = payload.get('source', '')
                                summary = payload.get('summary', '')
                                keywords = payload.get('keywords', [])
                                questions = payload.get('questions', [])
                                period = payload.get('period', '')
                                quarter = payload.get('quarter', '')
                                report_type = payload.get('report_type', '')
                                report_date = payload.get('report_date', '')
                                currency = payload.get('currency', '')

                            if not content:
                                continue

                            score = point.score
                            logger.info(f"  Point {idx+1}: score={score:.4f}, company={company}, ticker={ticker}, period={period} Q{quarter if quarter else 'N/A'}")
                            logger.info(f"    Content preview: {content[:100]}...")

                            doc = Document(
                                page_content=content,
                                metadata={
                                    "source": source,
                                    "summary": summary,
                                    "keywords": keywords,
                                    "questions": questions,
                                    "company": company,
                                    "ticker": ticker,
                                    "period": str(period) if period else "",
                                    "quarter": str(quarter) if quarter else "",
                                    "report_type": report_type,
                                    "report_date": report_date,
                                    "currency": currency,
                                    "collection": collection_name,
                                }
                            )
                            all_documents.append((score, doc))
                except Exception as e:
                    logger.error(f"Error searching collection {collection_name}: {e}")

            all_documents.sort(key=lambda x: x[0], reverse=True)
            documents = [doc for _, doc in all_documents[:k]]

            logger.info(f"Found {len(documents)} relevant chunks (requested {k})")
            if not documents:
                logger.warning(f"No documents found for query: {query}")
            return documents
        except Exception as e:
            logger.error(f"Error searching chunks: {e}", exc_info=True)
            return []

    def build_context(self, documents: List[Document]) -> str:
        if not documents:
            return ""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            company = doc.metadata.get('company', 'Unknown')
            period = doc.metadata.get('period', '')
            quarter = doc.metadata.get('quarter', '')
            period_str = f" {period} {quarter} квартал" if period and quarter else f" {period}" if period else ""
            context_parts.append(f"[Документ {i}: {company}{period_str}]\n{doc.page_content}\n")
        context = "\n---\n".join(context_parts)
        logger.info(f"Built context with {len(documents)} documents, total length: {len(context)} chars")
        return context

    def _get_doc_display_name(self, doc_name: str) -> str:
        return doc_name

    async def get_rag_response(self, query: str, user_id: Optional[int] = None, reporting_mode: bool = False) -> Dict[str, Any]:
        cache_key = f"rag_response:{hashlib.md5(query.encode()).hexdigest()}:{reporting_mode}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Returning cached response for query: {query[:50]}...")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis cache error: {e}")

        top_k = self.reporting_top_k if reporting_mode else self.normal_top_k
        logger.info(f"Using top_k={top_k} (reporting_mode={reporting_mode})")

        relevant_docs = await self.search_relevant_chunks(query, top_k=top_k, reporting_mode=reporting_mode)
        context = self.build_context(relevant_docs)
        documents_used = list(set([doc.metadata.get('company', 'Unknown') for doc in relevant_docs]))

        result = {
            "query": query,
            "context_used": bool(context),
            "chunks_count": len(relevant_docs),
            "documents_used": documents_used,
            "context": context,
            "reporting_mode": reporting_mode,
            "top_k_used": top_k
        }

        logger.info(f"RAG result: context_used={result['context_used']}, chunks={result['chunks_count']}, docs={documents_used}")

        try:
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")

        return result