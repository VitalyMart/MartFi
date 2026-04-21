import os
import re
import json
import time
import logging
import textwrap
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TOKEN_ROUTER_DB")
if not API_KEY:
    raise ValueError("TOKEN_ROUTER_DB not found in .env")

MODEL = os.getenv("CHUNKER_MODEL", "qwen/qwen-2.5-7b-instruct")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_LINE_LENGTH = 120
SPLIT_MARKER = "<SPLIT>"

IFRS_TXT_ROOT = Path("rag_knowledge_data/data/txt/IFRS")
OUTPUT_JSON_DIR = Path("rag_knowledge_data/data_processed/json/ifrs")
OUTPUT_TXT_DIR = Path("rag_knowledge_data/data_processed/txt/ifrs")

ALLOWED_TICKERS = {
    "GAZP", "GMKN", "LKOH", "MOEX", "NVTK", "OZON", "PLZL", "ROSN",
    "SBER", "SNGS", "T", "TATN", "VTBR", "X5", "YDEX"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""
Ты — ассистент для подготовки базы знаний из финансовых отчётов (МСФО).

Твоя задача:
1. Сначала извлеки метаданные документа в формате:
===METADATA===
company: название компании
ticker: тикер компании (GAZP, SBER, LKOH и т.д.)
period: год отчёта (например, 2025)
report_type: quarter или year
quarter: номер квартала (1-4) если report_type=quarter, иначе None
report_date: дата публикации отчёта в формате YYYY-MM-DD
currency: валюта отчёта (RUB, USD, EUR)
===END_METADATA===

2. Затем раздели текст на смысловые блоки, вставив метку {SPLIT_MARKER} между ними.
3. Для каждого блока добавь метаданные в формате:

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
- <questions> пиши через |, 1-2 вопроса.
- Верни сначала METADATA, потом размеченные блоки.
- Не используй китайский язык.
- Обязательно заполни все поля METADATA.
""".strip()

def extract_year_from_filename(file_path: Path) -> str:
    match = re.search(r'20\d{2}', str(file_path))
    return match.group(0) if match else "2025"

def extract_quarter_from_filename(file_path: Path) -> Optional[int]:
    match = re.search(r'q([1-4])', str(file_path).lower())
    return int(match.group(1)) if match else None

def wrap_long_lines(text: str, max_length: int = MAX_LINE_LENGTH) -> str:
    lines = text.split('\n')
    wrapped = []
    for line in lines:
        if not line.strip() or '===CHUNK' in line or ('<' in line and '>' in line):
            wrapped.append(line)
            continue
        wrapped.append(textwrap.fill(line, width=max_length, break_long_words=False, break_on_hyphens=False))
    return '\n'.join(wrapped)

def call_llm(text: str) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "IFRS Processor"
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
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise

def parse_chunks_only(full_response: str) -> List[Dict[str, Any]]:
    chunks = []
    blocks = full_response.split('===CHUNK_END===')
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
                }
                chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Error parsing chunk: {e}")
            continue
    return chunks

def parse_metadata_and_chunks(full_response: str, folder_ticker: str, file_path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    metadata = {}
    
    meta_match = re.search(r'===METADATA===(.*?)===END_METADATA===', full_response, re.DOTALL)
    if meta_match:
        for line in meta_match.group(1).strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if value.lower() == 'none':
                    value = None
                elif key == 'quarter' and value is not None:
                    try:
                        value = int(value)
                    except ValueError:
                        value = None
                metadata[key] = value
    
    if not metadata.get('ticker'):
        metadata['ticker'] = folder_ticker
    
    if not metadata.get('period'):
        metadata['period'] = extract_year_from_filename(file_path)
    
    if not metadata.get('quarter'):
        quarter = extract_quarter_from_filename(file_path)
        if quarter:
            metadata['quarter'] = quarter
            metadata['report_type'] = 'quarter'
        else:
            metadata['report_type'] = 'year'
    
    if not metadata.get('company'):
        company_names = {
            "GAZP": "Газпром", "GMKN": "Норильский никель", "LKOH": "Лукойл",
            "MOEX": "Московская биржа", "NVTK": "Новатэк", "OZON": "Озон",
            "PLZL": "Полюс", "ROSN": "Роснефть", "SBER": "Сбер",
            "SNGS": "Сургутнефтегаз", "T": "МТС", "TATN": "Татнефть",
            "VTBR": "ВТБ", "X5": "X5 Group", "YDEX": "Яндекс"
        }
        metadata['company'] = company_names.get(folder_ticker, folder_ticker)
    
    if not metadata.get('currency'):
        metadata['currency'] = "RUB"
    
    if not metadata.get('report_date'):
        metadata['report_date'] = None
    
    clean_response = re.sub(r'===METADATA===.*?===END_METADATA===', '', full_response, flags=re.DOTALL).strip()
    
    chunks = parse_chunks_only(clean_response)
    
    if not chunks:
        chunks = parse_chunks_only(full_response)
    
    return metadata, chunks

def save_chunks(chunks: List[Dict], source_filename: str, metadata: Dict):
    OUTPUT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_TXT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_JSON_DIR / f"{source_filename}.jsonl"
    txt_path = OUTPUT_TXT_DIR / f"{source_filename}.txt"

    with open(json_path, 'w', encoding='utf-8') as f_json:
        for chunk in chunks:
            chunk_with_meta = {**metadata, **chunk}
            searchable_text = f"{chunk['summary']} {' '.join(chunk['keywords'])} {' '.join(chunk['questions'])} {chunk['content']}"
            chunk_with_meta['searchable_text'] = wrap_long_lines(searchable_text)
            chunk_with_meta['content'] = wrap_long_lines(chunk['content'])
            chunk_with_meta['source'] = source_filename
            f_json.write(json.dumps(chunk_with_meta, ensure_ascii=False) + '\n')

    with open(txt_path, 'w', encoding='utf-8') as f_txt:
        for i, chunk in enumerate(chunks, 1):
            f_txt.write(f"\n--- CHUNK {i} ---\n")
            for k, v in metadata.items():
                if v is not None:
                    f_txt.write(f"[{k.capitalize()}] {v}\n")
            f_txt.write(f"[Summary] {chunk['summary']}\n")
            f_txt.write(f"[Keywords] {', '.join(chunk['keywords'])}\n")
            f_txt.write(f"[Questions] {' | '.join(chunk['questions'])}\n")
            f_txt.write(f"[Content]\n{wrap_long_lines(chunk['content'])}\n")

    logger.info(f"Saved {len(chunks)} chunks to {json_path}")

def process_file(file_path: Path, folder_ticker: str):
    logger.info(f"Processing {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if len(content) > 100000:
        logger.warning(f"File too large ({len(content)} chars), skipping: {file_path}")
        return

    try:
        llm_output = call_llm(content)
        metadata, chunks = parse_metadata_and_chunks(llm_output, folder_ticker, file_path)
        
        ticker = metadata.get('ticker', folder_ticker)
        if ticker not in ALLOWED_TICKERS:
            ticker = folder_ticker
        
        period = metadata.get('period', '2025')
        quarter = metadata.get('quarter')
        
        if quarter:
            source_filename = f"{ticker}_{period}_Q{quarter}"
        else:
            source_filename = f"{ticker}_{period}"
        
        if chunks:
            save_chunks(chunks, source_filename, metadata)
        else:
            logger.warning(f"No chunks extracted from {file_path}")
            
            fallback_chunk = {
                "content": content[:5000] if len(content) > 5000 else content,
                "summary": f"Отчёт компании {metadata.get('company', ticker)} за {period} год",
                "keywords": [ticker, "финансовый отчёт", "МСФО"],
                "questions": [f"Какие финансовые показатели у {ticker} за {period} год?"]
            }
            save_chunks([fallback_chunk], source_filename, metadata)
            logger.info(f"Saved fallback chunk for {file_path}")

        time.sleep(1)

    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")

def walk_ifrs_directory():
    if not IFRS_TXT_ROOT.exists():
        logger.error(f"IFRS root not found: {IFRS_TXT_ROOT}")
        return

    quarter_root = IFRS_TXT_ROOT / "quarter"
    if quarter_root.exists():
        for company_dir in quarter_root.iterdir():
            if not company_dir.is_dir():
                continue
            folder_ticker = company_dir.name
            if folder_ticker not in ALLOWED_TICKERS:
                logger.warning(f"Unknown ticker in folder: {folder_ticker}, skipping")
                continue
            for q_file in sorted(company_dir.glob("q*.txt")):
                process_file(q_file, folder_ticker)

    year_root = IFRS_TXT_ROOT / "year"
    if year_root.exists():
        for company_dir in year_root.iterdir():
            if not company_dir.is_dir():
                continue
            folder_ticker = company_dir.name
            if folder_ticker not in ALLOWED_TICKERS:
                logger.warning(f"Unknown ticker in folder: {folder_ticker}, skipping")
                continue
            for year_file in company_dir.glob(f"{folder_ticker}*.txt"):
                process_file(year_file, folder_ticker)

def main():
    logger.info("Starting IFRS processing with LLM metadata extraction")
    walk_ifrs_directory()
    logger.info("Done")

if __name__ == "__main__":
    main()