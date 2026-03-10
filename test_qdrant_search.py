import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

HF_TOKEN = os.getenv("TOKEN_HUGGINGFACE")
if not HF_TOKEN:
    raise ValueError("TOKEN_HUGGINGFACE not found in .env")

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "finance_knowledge"

TEST_QUERIES = [
    "Какие риски у корпоративных облигаций?",
    "Что такое ИИС и какие льготы он даёт?",
    "Какие компании входят в топ-3 индекса МосБиржи?",
    "Как заработать на акциях?",
    "Какие комиссии у биржевых фондов?",
    "Чем отличаются обыкновенные акции от привилегированных?",
]


def initialize_model(model_name: str, hf_token: str) -> SentenceTransformer:
    logger.info(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name, token=hf_token)
    logger.info(f"Model loaded successfully. Vector size: {model.get_sentence_embedding_dimension()}")
    return model


def initialize_qdrant_client(host: str, port: int) -> QdrantClient:
    logger.info(f"Connecting to Qdrant at {host}:{port}")
    client = QdrantClient(host=host, port=port)
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    logger.info(f"Available collections: {collection_names}")
    return client


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    collections = client.get_collections().collections
    return any(c.name == collection_name for c in collections)


def search_query(
    client: QdrantClient,
    model: SentenceTransformer,
    collection_name: str,
    query: str,
    top_k: int = 3
) -> list:
    query_vector = model.encode(query).tolist()
    
    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        with_payload=True,
        with_vectors=False
    )
    
    return results.points


def display_results(query: str, results: list) -> None:
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    
    if not results:
        print("No results found.")
        return
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. Score: {r.score:.4f} | Source: {r.payload.get('source', 'N/A')}")
        print(f"   Summary: {r.payload.get('summary', 'N/A')[:150]}...")
        keywords = r.payload.get('keywords', [])
        print(f"   Keywords: {', '.join(keywords[:3]) if keywords else 'N/A'}")
        print(f"   Questions: {r.payload.get('questions', ['N/A'])[0]}")


def run_tests(
    client: QdrantClient,
    model: SentenceTransformer,
    collection_name: str,
    queries: list
) -> dict:
    stats = {"total": len(queries), "success": 0, "failed": 0}
    
    for query in queries:
        try:
            results = search_query(client, model, collection_name, query)
            display_results(query, results)
            stats["success"] += 1
        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}")
            stats["failed"] += 1
    
    return stats


def main():
    try:
        model = initialize_model(MODEL_NAME, HF_TOKEN)
        client = initialize_qdrant_client(QDRANT_HOST, QDRANT_PORT)
        
        if not collection_exists(client, COLLECTION_NAME):
            logger.error(f"Collection '{COLLECTION_NAME}' not found in Qdrant")
            logger.error("Run index_to_qdrant.py first to populate the collection")
            return
        
        logger.info(f"Running {len(TEST_QUERIES)} test queries...")
        stats = run_tests(client, model, COLLECTION_NAME, TEST_QUERIES)
        
        print(f"\n{'='*80}")
        print(f"Test Summary: {stats['success']}/{stats['total']} queries successful")
        print(f"{'='*80}\n")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    main()