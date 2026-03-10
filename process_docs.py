import os
import time
import json
import logging
import requests
import textwrap
from dotenv import load_dotenv
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("TOKEN_ROUTER_DB")
if not API_KEY:
    raise ValueError("TOKEN_ROUTER_DB not found in .env")

INPUT_DIR = Path("rag_knowledge_data/data/txt")
OUTPUT_JSON_DIR = Path("rag_knowledge_data/data_processed/json")
OUTPUT_TXT_DIR = Path("rag_knowledge_data/data_processed/txt")

MODEL = os.getenv("CHUNKER_MODEL", "qwen/qwen-2.5-7b-instruct") 
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_LINE_LENGTH = 120
SPLIT_MARKER = "<SPLIT>"

SYSTEM_PROMPT = f"""
Ты — ассистент для подготовки базы знаний для финансового приложения.
Твоя задача:
1. Разделить текст на смысловые блоки, вставив метку {SPLIT_MARKER} между ними.
2. Для каждого блока добавить метаданные в формате:

===CHUNK_START===
<summary>Краткое описание сути блока (1-2 предложения)</summary>
<keywords>ключевое1, ключевое2, ключевое3</keywords>
<questions>Вопрос 1?|Вопрос 2?</questions>
<content>Исходный текст блока</content>
===CHUNK_END===

Правила:
- Сохраняй исходный текст в <content> без изменений.
- Не выдумывай факты, используй только информацию из текста.
- <keywords> пиши через запятую, 3-5 слов.
- <questions> пиши через |, 1-2 вопроса, на которые отвечает этот блок.
- Верни только размеченные блоки, без вступлений.
- Не используй китайский язык вообще
""".strip()


def wrap_long_lines(text: str, max_length: int = MAX_LINE_LENGTH) -> str:
    """Разбивает длинные строки, не разрывая слова."""
    lines = text.split('\n')
    wrapped = []
    for line in lines:
        if not line.strip() or '===CHUNK' in line or ('<' in line and '>' in line):
            wrapped.append(line)
            continue
        wrapped.append(textwrap.fill(line, width=max_length, break_long_words=False, break_on_hyphens=False))
    return '\n'.join(wrapped)


def process_text(text: str) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "RAG Chunker"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Обработай документ:\n\n{text}"}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        if not response.ok:
            logger.error(f"API Error {response.status_code}: {response.text}")
            response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise


def parse_chunks(markup: str) -> list[dict]:
    """Парсит размеченный текст в список словарей."""
    import re
    chunks = []
    blocks = markup.split('===CHUNK_END===')
    
    for block in blocks:
        if '===CHUNK_START===' not in block:
            continue
        block = block.replace('===CHUNK_START===', '').strip()
        
        try:
            summary = re.search(r'<summary>(.*?)</summary>', block, re.DOTALL)
            keywords = re.search(r'<keywords>(.*?)</keywords>', block, re.DOTALL)
            questions = re.search(r'<questions>(.*?)</questions>', block, re.DOTALL)
            content = re.search(r'<content>(.*?)</content>', block, re.DOTALL)
            
            if content:
                chunk = {
                    "content": content.group(1).strip(),
                    "summary": summary.group(1).strip() if summary else "",
                    "keywords": [k.strip() for k in keywords.group(1).split(',') if k.strip()] if keywords else [],
                    "questions": [q.strip() for q in questions.group(1).split('|') if q.strip()] if questions else [],
                    "source": None
                }
                chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Ошибка парсинга блока: {e}")
            continue
    
    return chunks


def save_chunks(chunks: list[dict], source_filename: str):
    OUTPUT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_TXT_DIR.mkdir(parents=True, exist_ok=True)
    
    json_path = OUTPUT_JSON_DIR / f"{source_filename}.jsonl"
    txt_path = OUTPUT_TXT_DIR / f"{source_filename}.txt"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            searchable_text = f"{chunk['summary']} {' '.join(chunk['keywords'])} {' '.join(chunk['questions'])} {chunk['content']}"
            chunk['searchable_text'] = wrap_long_lines(searchable_text)
            chunk['content'] = wrap_long_lines(chunk['content'])
            chunk['source'] = source_filename
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(chunks, 1):
            f.write(f"\n--- CHUNK {i} ---\n")
            f.write(f"[Summary] {chunk['summary']}\n")
            f.write(f"[Keywords] {', '.join(chunk['keywords'])}\n")
            f.write(f"[Questions] {' | '.join(chunk['questions'])}\n")
            f.write(f"[Content]\n{wrap_long_lines(chunk['content'])}\n")
    
    return json_path, txt_path


def main():
    files = list(INPUT_DIR.glob("*.txt"))
    
    if not files:
        logger.warning(f"No .txt files found in {INPUT_DIR}")
        return

    logger.info(f"Found {len(files)} files. Using model: {MODEL}")

    for file_path in files:
        try:
            logger.info(f"Processing: {file_path.name}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if len(content) > 100000:
                logger.warning(f"Skipping {file_path.name}: too large")
                continue

            result = process_text(content)
            chunks = parse_chunks(result)
            
            if not chunks:
                logger.warning(f"No chunks parsed from {file_path.name}")
                continue
            
            save_chunks(chunks, file_path.stem)
            logger.info(f"Saved {len(chunks)} chunks from {file_path.name}")
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")


if __name__ == "__main__":
    main()