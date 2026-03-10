import os
from dotenv import load_dotenv

load_dotenv()

class QdrantSettings:
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "finance_knowledge")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    HF_TOKEN = os.getenv("TOKEN_HUGGINGFACE")

qdrant_settings = QdrantSettings()