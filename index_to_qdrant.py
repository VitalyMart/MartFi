import json
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from back.config_qdrant import qdrant_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

JSONL_DIR = Path("rag_knowledge_data/data_processed/json")


def create_collection_if_not_exists(client, collection_name, vector_size):
    collections = client.get_collections().collections
    if not any(c.name == collection_name for c in collections):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Collection '{collection_name}' created")
    else:
        logger.info(f"Collection '{collection_name}' already exists")


def generate_qdrant_id(source: str, content: str) -> int:
    hash_hex = hashlib.md5(f"{source}:{content}".encode()).hexdigest()
    return int(hash_hex, 16) % (2 ** 63 - 1)


def load_documents(jsonl_dir: Path) -> List[Tuple[Document, int]]:
    documents = []
    for file in jsonl_dir.glob("*.jsonl"):
        with open(file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    chunk = json.loads(line)
                    content = chunk.get("content", "")
                    if not content:
                        continue
                    doc_id = generate_qdrant_id(chunk.get("source", file.stem), content)
                    metadata = {
                        "source": chunk.get("source", file.stem),
                        "summary": chunk.get("summary", ""),
                        "keywords": ", ".join(chunk.get("keywords", [])),
                        "questions": ", ".join(chunk.get("questions", [])),
                    }
                    doc = Document(
                        page_content=content,
                        metadata=metadata,
                    )
                    documents.append((doc, doc_id))
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"JSON decode error in {file.name}:{line_num}: {e}"
                    )
                except Exception as e:
                    logger.error(f"Error processing chunk in {file.name}:{line_num}: {e}")
    logger.info(f"Loaded {len(documents)} documents")
    return documents


def index_to_qdrant():
    logger.info(f"Loading embedding model: {qdrant_settings.EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=qdrant_settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    client = QdrantClient(
        host=qdrant_settings.QDRANT_HOST,
        port=qdrant_settings.QDRANT_PORT,
    )
    dummy_embedding = embeddings.embed_query("test")
    vector_size = len(dummy_embedding)
    create_collection_if_not_exists(
        client, qdrant_settings.COLLECTION_NAME, vector_size
    )
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=qdrant_settings.COLLECTION_NAME,
        embedding=embeddings,
    )
    documents_with_ids = load_documents(JSONL_DIR)
    if not documents_with_ids:
        logger.error("No documents found")
        return
    try:
        texts = [doc.page_content for doc, _ in documents_with_ids]
        metadatas = [doc.metadata for doc, _ in documents_with_ids]
        ids = [str(doc_id) for _, doc_id in documents_with_ids]
        vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids, batch_size=64)
        logger.info(f"Indexing completed. Total documents: {len(documents_with_ids)}")
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise


if __name__ == "__main__":
    index_to_qdrant()