import json
import asyncio
import aiohttp
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from back.services.rag_service import RAGService
from back.core.redis_client import redis_client

LLM_METRICS_PROMPT = """Ты - эксперт по оценке RAG систем. Оцени ответ RAG системы по следующим метрикам.

ВОПРОС: {question}
ЭТАЛОННЫЙ ОТВЕТ: {ground_truth}
ОТВЕТ RAG: {rag_answer}
КОНТЕКСТ (использованные документы): {context}

Оцени по шкале от 0.0 до 1.0 следующие метрики:

1. answer_relevance (релевантность ответа вопросу) - насколько ответ соответствует вопросу
2. factual_accuracy (фактическая точность) - насколько факты в ответе совпадают с эталоном
3. completeness (полнота) - насколько ответ покрывает все аспекты эталонного ответа
4. conciseness (краткость) - насколько ответ лаконичен без потери смысла
5. context_adherence (следование контексту) - насколько ответ основан только на предоставленном контексте
6. hallucination_score (отсутствие галлюцинаций) - 1.0 если нет выдуманных фактов, 0.0 если есть
7. numerical_accuracy (точность чисел) - насколько числа в ответе совпадают с эталоном

Ответь ТОЛЬКО в формате JSON:
{{
    "answer_relevance": 0.0,
    "factual_accuracy": 0.0,
    "completeness": 0.0,
    "conciseness": 0.0,
    "context_adherence": 0.0,
    "hallucination_score": 0.0,
    "numerical_accuracy": 0.0,
    "reasoning": "краткое объяснение"
}}"""

FAST_MATCH_PROMPT = """Сравни эталонный ответ и ответ RAG системы. Ответь ТОЛЬКО "ДА" или "НЕТ".

Эталон: {ground_truth}
Ответ RAG: {rag_answer}
Вопрос: {question}

Совпадают ли ответы по смыслу?"""

async def llm_evaluate_single(ground_truth: str, rag_answer: str, question: str, context: str, api_key: str) -> Dict[str, Any]:
    if not rag_answer or not ground_truth:
        return {
            "answer_relevance": 0.0,
            "factual_accuracy": 0.0,
            "completeness": 0.0,
            "conciseness": 0.0,
            "context_adherence": 0.0,
            "hallucination_score": 0.0,
            "numerical_accuracy": 0.0,
            "reasoning": "Empty answer or ground truth"
        }
    
    if "Ошибка" in rag_answer or len(rag_answer) < 2:
        return {
            "answer_relevance": 0.0,
            "factual_accuracy": 0.0,
            "completeness": 0.0,
            "conciseness": 0.0,
            "context_adherence": 0.0,
            "hallucination_score": 0.0,
            "numerical_accuracy": 0.0,
            "reasoning": "Error or too short answer"
        }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = LLM_METRICS_PROMPT.format(
        question=question[:500],
        ground_truth=ground_truth[:500],
        rag_answer=rag_answer[:500],
        context=context[:1000]
    )
    
    payload = {
        "model": "qwen/qwen-2.5-72b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    content = content.replace('```json', '').replace('```', '')
                    result = json.loads(content)
                    return result
                else:
                    return {"answer_relevance": 0.0, "factual_accuracy": 0.0, "completeness": 0.0, "conciseness": 0.0, "context_adherence": 0.0, "hallucination_score": 0.0, "numerical_accuracy": 0.0, "reasoning": f"API error: {response.status}"}
    except Exception as e:
        return {"answer_relevance": 0.0, "factual_accuracy": 0.0, "completeness": 0.0, "conciseness": 0.0, "context_adherence": 0.0, "hallucination_score": 0.0, "numerical_accuracy": 0.0, "reasoning": f"Exception: {str(e)}"}

async def llm_fast_match(ground_truth: str, rag_answer: str, question: str, api_key: str) -> bool:
    if not rag_answer or not ground_truth:
        return False
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = FAST_MATCH_PROMPT.format(
        ground_truth=ground_truth[:300],
        rag_answer=rag_answer[:300],
        question=question[:200]
    )
    
    payload = {
        "model": "qwen/qwen-2.5-72b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 10
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data["choices"][0]["message"]["content"].strip().upper()
                    return result == "ДА"
                else:
                    return False
    except Exception as e:
        return False

async def generate_answer_with_openrouter(query: str, context: str, api_key: str) -> str:
    if not api_key:
        return "Ошибка: TOKEN_ROUTER не настроен"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = f"""Ты - финансовый ассистент. Отвечай ТОЛЬКО на основе предоставленного контекста.
Если точного ответа (включая числа) нет в контексте, ответь: "Информация не найдена в предоставленных документах".

КОНТЕКСТ:
{context}

ВОПРОС: {query}

ОТВЕТ (только факт, без лишних слов):"""
    
    payload = {
        "model": "qwen/qwen-2.5-72b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    return f"Ошибка API: {response.status}"
    except Exception as e:
        return f"Ошибка: {e}"

async def clear_rag_cache():
    try:
        keys = await redis_client.keys("rag_response:*")
        if keys:
            await redis_client.delete(*keys)
            print("RAG cache cleared")
        else:
            print("No cache keys found")
    except Exception as e:
        print(f"Failed to clear cache: {e}")

async def evaluate_rag_llm_based(questions_path: str, output_path: str = "rag_llm_evaluation.json") -> Dict[str, Any]:
    await clear_rag_cache()
    
    with open(questions_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions_answers = data.get('questions_answers', data.get('questions', []))
    if not questions_answers:
        raise ValueError("JSON должен содержать 'questions_answers'")
    
    rag = RAGService()
    api_key = os.getenv("TOKEN_ROUTER")
    
    if not api_key:
        print("WARNING: TOKEN_ROUTER not set, LLM evaluation will fail")
    
    results = []
    total_scores = {
        "answer_relevance": 0.0,
        "factual_accuracy": 0.0,
        "completeness": 0.0,
        "conciseness": 0.0,
        "context_adherence": 0.0,
        "hallucination_score": 0.0,
        "numerical_accuracy": 0.0
    }
    
    correct_binary = 0
    total_tokens_estimated = 0
    
    print(f"\n{'='*80}")
    print(f"LLM-BASED RAG EVALUATION")
    print(f"Total questions: {len(questions_answers)}")
    print(f"{'='*80}\n")
    
    for idx, qa in enumerate(questions_answers, 1):
        question = qa.get('question', '')
        ground_truth = qa.get('answer', '')
        
        if not question or not ground_truth:
            print(f"Skipping question {idx} - missing data")
            continue
        
        print(f"[{idx}/{len(questions_answers)}] {question[:70]}...")
        
        rag_response = await rag.get_rag_response(query=question, user_id=None, reporting_mode=True)
        context = rag_response.get('context', '')
        chunks_count = rag_response.get('chunks_count', 0)
        documents_used = rag_response.get('documents_used', [])
        
        if context and len(context) > 100:
            answer = await generate_answer_with_openrouter(question, context, api_key)
        else:
            answer = "Информация не найдена в предоставленных документах"
        
        is_correct = False
        metrics = None
        
        if api_key:
            metrics = await llm_evaluate_single(ground_truth, answer, question, context, api_key)
            
            for metric_name in total_scores.keys():
                if metric_name in metrics:
                    total_scores[metric_name] += metrics[metric_name]
            
            is_correct = metrics.get("factual_accuracy", 0.0) >= 0.7
            if is_correct:
                correct_binary += 1
            
            print(f"   Factual accuracy: {metrics.get('factual_accuracy', 0):.2f}")
            print(f"   Hallucination score: {metrics.get('hallucination_score', 0):.2f}")
            print(f"   Numerical accuracy: {metrics.get('numerical_accuracy', 0):.2f}")
        else:
            print(f"   No LLM evaluation (missing API key)")
        
        print(f"   Binary correct: {is_correct}")
        print(f"   Chunks: {chunks_count}, Sources: {documents_used}")
        print()
        
        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "rag_answer": answer,
            "is_correct_binary": is_correct,
            "llm_metrics": metrics if metrics else {},
            "chunks_count": chunks_count,
            "documents_used": documents_used,
            "context_preview": context[:500] if context else ""
        })
        
        total_tokens_estimated += len(question) + len(ground_truth) + len(answer) + len(context)
        
        await asyncio.sleep(0.1)
    
    num_valid = len([r for r in results if r.get("llm_metrics")])
    avg_scores = {}
    for metric_name in total_scores:
        avg_scores[metric_name] = total_scores[metric_name] / num_valid if num_valid > 0 else 0
    
    binary_accuracy = (correct_binary / len(results)) * 100 if results else 0
    
    final_results = {
        "test_config": {
            "evaluation_method": "llm_based",
            "reporting_mode": True,
            "timestamp": datetime.now().isoformat(),
            "metrics_used": list(total_scores.keys())
        },
        "total_questions": len(results),
        "binary_accuracy": binary_accuracy,
        "binary_correct": correct_binary,
        "average_scores": avg_scores,
        "aggregated_metrics": {
            "overall_quality": sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0,
            "factual_quality": avg_scores.get("factual_accuracy", 0),
            "hallucination_free": avg_scores.get("hallucination_score", 0),
            "relevance": avg_scores.get("answer_relevance", 0)
        },
        "chunks_statistics": {
            "avg_chunks_per_query": sum(r["chunks_count"] for r in results) / len(results) if results else 0,
            "total_chunks_retrieved": sum(r["chunks_count"] for r in results)
        },
        "source_usage": dict(Counter([doc for r in results for doc in r["documents_used"]])),
        "detailed_results": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print(f"EVALUATION COMPLETE")
    print(f"Results saved to: {output_path}")
    print(f"\nBINARY ACCURACY: {binary_accuracy:.1f}% ({correct_binary}/{len(results)})")
    print(f"\nLLM-BASED METRICS (0-1 scale):")
    for metric, score in avg_scores.items():
        print(f"   {metric}: {score:.3f}")
    print(f"\nOVERALL QUALITY SCORE: {final_results['aggregated_metrics']['overall_quality']:.3f}")
    print(f"{'='*80}")
    
    return final_results

def generate_detailed_report(results_path: str = "rag_llm_evaluation.json") -> Dict[str, Any]:
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*80)
    print("DETAILED RAG DIAGNOSTICS REPORT")
    print("="*80)
    
    print(f"\nEXECUTIVE SUMMARY:")
    print(f"   Total queries evaluated: {data['total_questions']}")
    print(f"   Binary accuracy: {data['binary_accuracy']:.1f}%")
    print(f"   Overall quality score: {data['aggregated_metrics']['overall_quality']:.3f}")
    
    print(f"\nDETAILED METRICS BREAKDOWN:")
    for metric, score in data['average_scores'].items():
        rating = "EXCELLENT" if score >= 0.8 else "GOOD" if score >= 0.6 else "FAIR" if score >= 0.4 else "POOR"
        print(f"   {metric:25s}: {score:.3f} - {rating}")
    
    print(f"\nBOTTOM PERFORMING QUESTIONS (lowest factual_accuracy):")
    sorted_results = sorted(data['detailed_results'], key=lambda x: x.get('llm_metrics', {}).get('factual_accuracy', 0))
    for i, item in enumerate(sorted_results[:5], 1):
        fa = item.get('llm_metrics', {}).get('factual_accuracy', 0)
        print(f"\n   {i}. {item['question'][:80]}...")
        print(f"      Factual accuracy: {fa:.2f}")
        print(f"      Expected: {item['ground_truth'][:100]}")
        print(f"      Got: {item['rag_answer'][:100]}")
    
    print(f"\nHALLUCINATION ANALYSIS:")
    hallucinated = [r for r in data['detailed_results'] if r.get('llm_metrics', {}).get('hallucination_score', 1) < 0.5]
    print(f"   High hallucination risk: {len(hallucinated)}/{data['total_questions']} ({len(hallucinated)/data['total_questions']*100:.1f}%)")
    
    for i, item in enumerate(hallucinated[:3], 1):
        hs = item.get('llm_metrics', {}).get('hallucination_score', 0)
        print(f"\n   {i}. {item['question'][:70]}...")
        print(f"      Hallucination score: {hs:.2f}")
        print(f"      Answer: {item['rag_answer'][:100]}")
    
    print("\n" + "="*80)
    
    return data

async def main():
    questions_file = "metrics_data/questions_answers.json"
    
    if not os.path.exists(questions_file):
        print(f"ERROR: {questions_file} not found!")
        print("Please create a JSON file with 'questions_answers' array containing 'question' and 'answer' fields")
        return
    
    print("Starting LLM-based RAG evaluation...")
    print("Note: This will use OpenRouter API for comprehensive metric calculation")
    
    results = await evaluate_rag_llm_based(
        questions_path=questions_file,
        output_path="rag_llm_evaluation.json"
    )
    
    generate_detailed_report("rag_llm_evaluation.json")
    
    print("\nEvaluation complete!")

if __name__ == "__main__":
    asyncio.run(main())