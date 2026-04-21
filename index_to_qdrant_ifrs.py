import json
import hashlib
import uuid
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

IFRS_JSONL_DIR = Path("rag_knowledge_data/data_processed/json/ifrs")

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

def generate_qdrant_id(source: str, content: str) -> str:
    hash_hex = hashlib.md5(f"{source}:{content}".encode()).hexdigest()
    return str(uuid.UUID(hash_hex[:32]))

def load_documents(jsonl_dir: Path) -> List[Tuple[Document, str]]:
    documents = []
    if not jsonl_dir.exists():
        logger.error(f"Directory not found: {jsonl_dir}")
        return documents
    
    files = list(jsonl_dir.glob("*.jsonl"))
    logger.info(f"Found {len(files)} JSONL files in {jsonl_dir}")
    
    for file in files:
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
                        "company": chunk.get("company", ""),
                        "ticker": chunk.get("ticker", ""),
                        "period": chunk.get("period", ""),
                        "quarter": chunk.get("quarter"),
                        "report_type": chunk.get("report_type", ""),
                        "report_date": chunk.get("report_date", ""),
                        "currency": chunk.get("currency", ""),
                    }
                    
                    doc = Document(
                        page_content=content,
                        metadata=metadata,
                    )
                    documents.append((doc, doc_id))
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error in {file.name}:{line_num}: {e}")
                except Exception as e:
                    logger.error(f"Error processing chunk in {file.name}:{line_num}: {e}")
    
    logger.info(f"Loaded {len(documents)} documents from IFRS reports")
    return documents

def index_ifrs_to_qdrant():
    logger.info("="*60)
    logger.info("Indexing IFRS reports to Qdrant")
    logger.info("="*60)
    
    logger.info(f"Loading embedding model: {qdrant_settings.EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=qdrant_settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu", "token": qdrant_settings.HF_TOKEN},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    client = QdrantClient(
        host=qdrant_settings.QDRANT_HOST,
        port=qdrant_settings.QDRANT_PORT,
    )
    
    dummy_embedding = embeddings.embed_query("test")
    vector_size = len(dummy_embedding)
    
    collection_name = f"{qdrant_settings.COLLECTION_NAME}_ifrs"
    create_collection_if_not_exists(client, collection_name, vector_size)
    
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    
    documents_with_ids = load_documents(IFRS_JSONL_DIR)
    
    if not documents_with_ids:
        logger.error("No documents found in IFRS directory")
        return
    
    try:
        texts = [doc.page_content for doc, _ in documents_with_ids]
        metadatas = [doc.metadata for doc, _ in documents_with_ids]
        ids = [doc_id for _, doc_id in documents_with_ids]
        
        vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids, batch_size=64)
        
        logger.info("="*60)
        logger.info(f"Indexing completed successfully!")
        logger.info(f"Total documents indexed: {len(documents_with_ids)}")
        logger.info(f"Collection name: {collection_name}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise

if __name__ == "__main__":
    index_ifrs_to_qdrant()