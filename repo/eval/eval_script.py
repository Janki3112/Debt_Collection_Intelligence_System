"""
Evaluation script for Q&A system
"""
import json
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.retriever import retrieve_top_k
from app.core.llm_client import answer_with_optional_llm

def load_eval_set(filepath: str = "eval/qa_set.jsonl"):
    """Load evaluation questions"""
    questions = []
    with open(filepath, 'r') as f:
        for line in f:
            questions.append(json.loads(line))
    return questions

def evaluate_answer(answer: str, expected_keywords: list) -> float:
    """
    Simple keyword-based evaluation
    Returns score 0-1 based on keyword presence
    """
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords) if expected_keywords else 0.0

async def run_evaluation():
    """Run full evaluation"""
    questions = load_eval_set()
    
    scores = []
    results = []
    
    print("Running evaluation...")
    print(f"Total questions: {len(questions)}\n")
    
    for i, item in enumerate(questions, 1):
        question = item["question"]
        expected_kw = item.get("expected_keywords", [])
        category = item.get("category", "unknown")
        
        # Retrieve and answer
        chunks = retrieve_top_k(question, None, top_k=3)
        
        if not chunks:
            score = 0.0
            answer = "No relevant information found"
        else:
            answer, sources, model = answer_with_optional_llm(question, chunks)
            score = evaluate_answer(answer, expected_kw)
        
        scores.append(score)
        results.append({
            "question": question,
            "category": category,
            "score": score,
            "answer": answer[:200] + "..." if len(answer) > 200 else answer
        })
        
        print(f"[{i}/{len(questions)}] {category}: {score:.2f}")
    
    # Summary
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"Average Score: {avg_score:.3f}")
    print(f"Questions: {len(questions)}")
    print(f"{'='*60}\n")
    
    # Save results
    with open("eval/results.json", 'w') as f:
        json.dump({
            "average_score": avg_score,
            "total_questions": len(questions),
            "results": results
        }, f, indent=2)
    
    print("Results saved to eval/results.json")
    
    return avg_score

if __name__ == "__main__":
    asyncio.run(run_evaluation())