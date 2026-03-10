import json
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

JSONL_DIR = Path("rag_knowledge_data/data_processed/json")
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "finance_knowledge"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 64

def create_collection(client: QdrantClient, collection_name: str, vector_size: int):
    """Создаёт коллекцию, если она не существует."""
    collections = client.get_collections().collections
    if not any(c.name == collection_name for c in collections):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Коллекция '{collection_name}' создана")
    else:
        logger.info(f"Коллекция '{collection_name}' уже существует")

def load_chunks(jsonl_dir: Path) -> list[dict]:
    """Загружает все чанки из JSONL файлов."""
    chunks = []
    for file in jsonl_dir.glob("*.jsonl"):
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                chunk_id = f"{chunk['source']}_{abs(hash(chunk['content']))}"
                chunk['_id'] = chunk_id
                chunks.append(chunk)
    logger.info(f"Загружено {len(chunks)} чанков из {jsonl_dir}")
    return chunks

def index_to_qdrant():
    logger.info(f"Загрузка модели эмбеддингов: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    dummy_embedding = model.encode("тест")
    vector_size = len(dummy_embedding)
    
    create_collection(client, COLLECTION_NAME, vector_size)
    
    chunks = load_chunks(JSONL_DIR)
    if not chunks:
        logger.error("Чанки не найдены")
        return

    points = []
    for i, chunk in enumerate(chunks):
        embedding = model.encode(chunk["searchable_text"]).tolist()
        
        payload = {
            "source": chunk["source"],
            "keywords": chunk["keywords"],
            "summary": chunk["summary"],
            "questions": chunk["questions"],
            "content": chunk["content"]
        }
        
        points.append(PointStruct(id=abs(hash(chunk["_id"])), vector=embedding, payload=payload))
        
        if len(points) >= BATCH_SIZE:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(f"Индексировано {i + 1} из {len(chunks)}")
            points = []
    
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
    
    logger.info(f"✅ Индексация завершена. Всего чанков: {len(chunks)}")

if __name__ == "__main__":
    index_to_qdrant()