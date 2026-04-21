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
IFRS_COLLECTION_NAME = "finance_knowledge_ifrs"

TEST_QUERIES = [
    "Какие риски у корпоративных облигаций?",
    "Что такое ИИС и какие льготы он даёт?",
    "Какие компании входят в топ-3 индекса МосБиржи?",
    "Как заработать на акциях?",
    "Какие комиссии у биржевых фондов?",
    "Чем отличаются обыкновенные акции от привилегированных?",
    "Какая выручка у Озона за 3 квартал 2025 года?",
    "Сколько активных покупателей у Озона в 3 квартале 2025?",
    "Какие дивиденды рекомендовал совет директоров Озона?",
    "Какая чистая прибыль у Сбербанка за 2025 год?",
    "Какой прогноз по чистой прибыли у Сбербанка на 2026 год?",
    "Какая выручка у Роснефти за 2025 год?",
    "Как изменилась чистая прибыль Роснефти в 2025 году?",
    "Сколько золота произвел Полюс в 2025 году?",
    "Какие дивиденды у Полюса за 2025 год?",
    "Какова дивидендная доходность акций Полюса?",
    "Какое производство никеля у Норникеля во 2 квартале 2025?",
    "Почему Норникель понизил прогноз на 2025 год?",
    "Какая чистая прибыль у ВТБ за 2 квартал 2025?",
    "Какой прогноз по чистой прибыли ВТБ на 2025 год?",
    "Какая выручка у Московской биржи в 3 квартале 2025?",
    "Как изменились комиссионные доходы Мосбиржи в 3 квартале 2025?",
    "Какая EBITDA у Новатэка за 2025 год?",
    "Есть ли у Новатэка чистый долг на конец 2025 года?",
    "Какие дивиденды у Татнефти за 2025 год?",
    "Какая выручка у Татнефти за 4 квартал 2025?",
    "Почему ЛУКОЙЛ не раскрывает данные за 1 квартал 2025?",
    "Какая чистая прибыль у Газпрома за 2025 год?",
    "Какой свободный денежный поток у Газпрома в 2025?",
    "Какие факторы повлияли на рост Сбербанка в 2025 году?",
    "Сколько активных клиентов у Сбербанка в 2025?",
    "Какая рентабельность капитала у Сбербанка за 2025 год?",
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
        print(f"\n{i}. Score: {r.score:.4f}")
        print(f"   Source: {r.payload.get('source', 'N/A')}")
        print(f"   Company: {r.payload.get('company', 'N/A')}")
        print(f"   Ticker: {r.payload.get('ticker', 'N/A')}")
        print(f"   Period: {r.payload.get('period', 'N/A')}")
        print(f"   Quarter: {r.payload.get('quarter', 'N/A')}")
        print(f"   Report Date: {r.payload.get('report_date', 'N/A')}")
        print(f"   Summary: {r.payload.get('summary', 'N/A')[:200]}...")
        keywords = r.payload.get('keywords', [])
        print(f"   Keywords: {', '.join(keywords[:3]) if keywords else 'N/A'}")
        questions = r.payload.get('questions', [])
        print(f"   Questions: {questions[0] if questions else 'N/A'}")

def run_tests(
    client: QdrantClient,
    model: SentenceTransformer,
    queries: list
) -> dict:
    stats = {"total": len(queries), "success": 0, "failed": 0, "by_collection": {}}
    
    for collection_name in [COLLECTION_NAME, IFRS_COLLECTION_NAME]:
        if collection_exists(client, collection_name):
            stats["by_collection"][collection_name] = {"success": 0, "failed": 0}
            logger.info(f"Testing collection: {collection_name}")
    
    for query in queries:
        try:
            print(f"\n{'#'*80}")
            print(f"Testing query: {query}")
            print(f"{'#'*80}")
            
            for collection_name in [COLLECTION_NAME, IFRS_COLLECTION_NAME]:
                if not collection_exists(client, collection_name):
                    continue
                    
                results = search_query(client, model, collection_name, query)
                
                if results:
                    print(f"\n--- Results from {collection_name} ---")
                    for i, r in enumerate(results, 1):
                        print(f"\n  {i}. Score: {r.score:.4f}")
                        print(f"     Company: {r.payload.get('company', 'N/A')}")
                        print(f"     Period: {r.payload.get('period', 'N/A')}")
                        snippet = r.payload.get('content', r.payload.get('summary', ''))[:200]
                        print(f"     Snippet: {snippet}...")
                    stats["by_collection"][collection_name]["success"] += 1
                else:
                    print(f"\n--- No results from {collection_name} ---")
                    stats["by_collection"][collection_name]["failed"] += 1
                    
            stats["success"] += 1
            
        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}")
            stats["failed"] += 1
            
    return stats

def main():
    try:
        model = initialize_model(MODEL_NAME, HF_TOKEN)
        client = initialize_qdrant_client(QDRANT_HOST, QDRANT_PORT)
        
        logger.info(f"Testing with {len(TEST_QUERIES)} queries...")
        logger.info(f"Collections: {COLLECTION_NAME} and {IFRS_COLLECTION_NAME}")
        
        stats = run_tests(client, model, TEST_QUERIES)
        
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total queries: {stats['total']}")
        print(f"Successful: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        
        for collection_name, collection_stats in stats["by_collection"].items():
            print(f"\nCollection: {collection_name}")
            print(f"  Successful: {collection_stats['success']}")
            print(f"  Failed: {collection_stats['failed']}")
            
        print(f"{'='*80}\n")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    main()