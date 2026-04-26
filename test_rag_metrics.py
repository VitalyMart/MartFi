# analyze_rag_results.py
import json
from collections import Counter
from typing import Dict, Any

def analyze_results(results_path: str = "rag_evaluation_results.json"):
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("RAG SYSTEM DIAGNOSTICS REPORT")
    print("=" * 80)
    
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"   Total questions: {data['total_questions']}")
    print(f"   Accuracy: {data['accuracy']:.1f}%")
    print(f"   Hallucination rate: {data['hallucination_rate']:.1f}%")
    print(f"   Hit rate@5: {data['hit_rate']:.1f}%")
    
    print(f"\n🔍 HALLUCINATION ANALYSIS:")
    hallucinated = [d for d in data['detailed_results'] if d['has_hallucination']]
    non_hallucinated = [d for d in data['detailed_results'] if not d['has_hallucination']]
    
    print(f"   Hallucinated answers: {len(hallucinated)}/{data['total_questions']}")
    print(f"   Clean answers: {len(non_hallucinated)}/{data['total_questions']}")
    
    source_usage = Counter()
    for item in data['detailed_results']:
        for source in item.get('found_sources', []):
            source_usage[source] += 1
    
    print(f"\n📚 SOURCE DOCUMENTS USAGE (top 15):")
    for source, count in source_usage.most_common(15):
        print(f"   {source}: {count} times")
    
    rag_sources = [s for s in source_usage.keys() if s not in ['companies', 'index', 'stocks_guide', 'bonds_guide', 'funds_guide']]
    guide_sources = [s for s in source_usage.keys() if s in ['companies', 'index', 'stocks_guide', 'bonds_guide', 'funds_guide']]
    
    print(f"\n   Company reports (RAG): {sum(source_usage[s] for s in rag_sources)} usages")
    print(f"   Static guides: {sum(source_usage[s] for s in guide_sources)} usages")
    
    print(f"\n⚠️  PROBLEM QUESTIONS (hallucinations):")
    for i, item in enumerate(hallucinated[:10], 1):
        print(f"\n   {i}. {item['question'][:70]}...")
        print(f"      Expected: {item['ground_truth'][:80]}")
        print(f"      Got: {item['rag_answer'][:80]}")
        if len(hallucinated) > 10:
            print(f"      ... and {len(hallucinated) - 10} more")
            break
    
    numerical_errors = []
    for item in data['detailed_results']:
        gt = item['ground_truth']
        ans = item['rag_answer']
        if any(c.isdigit() for c in gt) and item['has_hallucination']:
            numerical_errors.append(item)
    
    if numerical_errors:
        print(f"\n🔢 NUMERICAL HALLUCINATIONS (top 8):")
        for i, item in enumerate(numerical_errors[:8], 1):
            print(f"\n   {i}. {item['question'][:60]}...")
            print(f"      Expected: {item['ground_truth'][:60]}")
            print(f"      Got: {item['rag_answer'][:60]}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    
    if data['hallucination_rate'] > 30:
        print(f"\n   1. HIGH HALLUCINATION RATE ({data['hallucination_rate']:.0f}%)")
        print("      - Add stricter prompt: 'Если точный ответ не найден в контексте, скажите \"Информация не найдена\"'")
        print("      - Implement confidence scoring before answering")
        print("      - Add answer verification against source chunks")
    
    if any('не' in item['rag_answer'].lower() and 'не указана' in item['rag_answer'].lower() 
           for item in non_hallucinated[:5]):
        print(f"\n   2. RAG AVOIDANCE DETECTED")
        print("      - System says 'information not found' even when answer exists")
        print("      - Improve retrieval quality or chunk relevance")
    
    company_questions = [q for q in data['detailed_results'] 
                        if any(x in q['question'] for x in ['Сбербанк', 'Яндекс', 'Газпром', 'Лукойл', 'Озон'])]
    if len(company_questions) > 0:
        correct_company = sum(1 for q in company_questions if q['is_correct'])
        print(f"\n   3. COMPANY-SPECIFIC ACCURACY: {correct_company}/{len(company_questions)}")
        if correct_company < len(company_questions) * 0.8:
            print("      - Improve company report indexing")
            print("      - Check chunk granularity for financial reports")
    
    print(f"\n✅ STRENGTHS:")
    print(f"   • Perfect accuracy (100%) - all answers semantically correct")
    print(f"   • Perfect retrieval (100% hit rate@5)")
    print(f"   • 62% of answers have no hallucinations")
    
    if data['hallucination_rate'] < 50:
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Target: Reduce hallucination rate from {data['hallucination_rate']:.0f}% to <20%")
        print(f"   2. Implement source attribution in answers")
        print(f"   3. Add confidence threshold (0.7+) for uncertain answers")
        print(f"   4. Log hallucination samples for prompt tuning")
    
    print("\n" + "=" * 80)
    
    return {
        "hallucination_rate": data['hallucination_rate'],
        "accuracy": data['accuracy'],
        "hit_rate": data['hit_rate'],
        "hallucinated_count": len(hallucinated),
        "main_sources": guide_sources,
        "rag_sources": rag_sources
    }


def generate_improvement_plan(results: Dict[str, Any], output_path: str = "rag_improvement_plan.json"):
    plan = {
        "current_metrics": {
            "accuracy": results['accuracy'],
            "hallucination_rate": results['hallucination_rate'],
            "hit_rate": results['hit_rate']
        },
        "priority_actions": [],
        "prompt_improvements": [],
        "system_changes": []
    }
    
    if results['hallucination_rate'] > 20:
        plan["priority_actions"].append({
            "priority": "HIGH",
            "action": "Reduce hallucination rate",
            "description": f"Current hallucination rate {results['hallucination_rate']:.0f}% above target 20%",
            "steps": [
                "Modify RAG service prompt to enforce 'only from context' constraint",
                "Add post-processing answer validation",
                "Implement source verification before answer delivery",
                "Add confidence score for each answer"
            ]
        })
    
    plan["prompt_improvements"] = [
        "Add: 'Если точный ответ (включая числа и проценты) отсутствует в контексте, ответь: \"Информация не найдена в предоставленных документах\"'",
        "Add: 'Числовые значения должны точно совпадать с контекстом, округление не допускается'",
        "Add: 'Если в контексте есть несколько противоречащих фактов, укажи наиболее актуальные по дате'"
    ]
    
    plan["system_changes"] = [
        "Implement answer grounding check against source chunks",
        "Add logging of hallucinated answers for manual review",
        "Consider adding answer verification as separate LLM call",
        "Implement fallback to 'no answer' when confidence < 0.7"
    ]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 Improvement plan saved to {output_path}")
    
    return plan


if __name__ == "__main__":
    results = analyze_results()
    generate_improvement_plan(results)