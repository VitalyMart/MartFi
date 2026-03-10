import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from ..core.logger import logger
from ..core.redis_client import redis_client

class RAGService:
    def __init__(self):
        self.knowledge_base_path = Path(__file__).parent.parent.parent / "rag_knowledge_data"
        self.documents = {}
        self.chunks = []
        self.chunk_size = 500
        self.chunk_overlap = 50
        self.cache_ttl = 3600
        self._load_documents()
        self._create_chunks()

    def _load_documents(self):
        if not self.knowledge_base_path.exists():
            logger.warning(f"Knowledge base path not found: {self.knowledge_base_path}")
            return
        for file_path in self.knowledge_base_path.glob("*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                doc_name = file_path.stem
                self.documents[doc_name] = {
                    'name': doc_name,
                    'content': content,
                    'path': str(file_path),
                    'loaded_at': datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error loading document {file_path}: {e}")

    def _create_chunks(self):
        self.chunks = []
        for doc_name, doc in self.documents.items():
            content = doc['content']
            words = content.split()
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk_words = words[i:i + self.chunk_size]
                if chunk_words:
                    chunk_text = ' '.join(chunk_words)
                    chunk_id = hashlib.md5(f"{doc_name}_{i}".encode()).hexdigest()
                    self.chunks.append({
                        'id': chunk_id,
                        'doc_name': doc_name,
                        'text': chunk_text,
                        'start_idx': i,
                        'end_idx': i + len(chunk_words)
                    })

    def search_relevant_chunks(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []
        query_words = set(query.lower().split())
        scored_chunks = []
        for chunk in self.chunks:
            chunk_text_lower = chunk['text'].lower()
            score = 0
            for word in query_words:
                if len(word) > 3:
                    score += chunk_text_lower.count(word)
            if score > 0:
                scored_chunks.append({'chunk': chunk, 'score': score, 'doc_name': chunk['doc_name']})
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        return [item['chunk'] for item in scored_chunks[:top_k]]

    def build_context(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return ""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            doc_name = chunk['doc_name']
            doc_display_name = self._get_doc_display_name(doc_name)
            context_parts.append(f"[Документ {i}: {doc_display_name}]\n{chunk['text']}\n")
        return "\n---\n".join(context_parts)

    def _get_doc_display_name(self, doc_name: str) -> str:
        display_names = {
            'bonds_guide': 'Руководство по облигациям',
            'companies': 'Информация о компаниях',
            'funds_guide': 'Руководство по фондам',
            'index': 'Индексы',
            'stocks_guide': 'Руководство по акциям'
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

        relevant_chunks = self.search_relevant_chunks(query)
        context = self.build_context(relevant_chunks)

        system_prompt = """Ты - финансовый ассистент MartFi, помогающий пользователям с инвестициями и финансовыми вопросами.
Ты отвечаешь на русском языке, используя предоставленный контекст из базы знаний.
Если в контексте нет информации для ответа, ты говоришь, что не нашел информации, но можешь дать общий совет на основе своих знаний.
Будь дружелюбным, полезным и точным.

ВАЖНОЕ ПРАВИЛО ДЛЯ ТАБЛИЦ:
- Если пишешь таблицу - используй HTML теги <table>, <tr>, <th>, <td> напрямую
- НЕ оборачивай HTML в блоки кода (```html или ```)
- НЕ используй markdown-таблицы (символы | и ---)
- HTML должен быть чистым, без обёрток, чтобы сразу отображался в интерфейсе

Пример правильного вывода таблицы:
<table>
<tr><th>Заголовок 1</th><th>Заголовок 2</th></tr>
<tr><td>Данные 1</td><td>Данные 2</td></tr>
</table>
"""
        user_prompt = f"""Контекст из базы знаний:
{context if context else "Контекст не найден."}

Вопрос пользователя: {query}

Ответь на вопрос используя информацию из контекста."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        result = {
            "query": query,
            "context_used": bool(context),
            "chunks_count": len(relevant_chunks),
            "documents_used": list(set(chunk['doc_name'] for chunk in relevant_chunks)),
            "messages": messages
        }

        try:
            await redis_client.setex(cache_key, self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")

        return result

    def get_documents_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": doc['name'],
                "display_name": self._get_doc_display_name(doc['name']),
                "size": len(doc['content']),
                "chunks": sum(1 for chunk in self.chunks if chunk['doc_name'] == doc['name'])
            }
            for doc in self.documents.values()
        ]

    async def refresh_knowledge_base(self):
        self.documents = {}
        self.chunks = []
        self._load_documents()
        self._create_chunks()
        return {
            "success": True,
            "documents_loaded": len(self.documents),
            "chunks_created": len(self.chunks)
        }