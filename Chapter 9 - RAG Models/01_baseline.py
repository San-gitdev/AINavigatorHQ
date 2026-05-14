# 01_baseline.py — Act 1: The Amnesiac Model
#
# Usage:
#   python 01_baseline.py                        # Tier B paid, interactive doc picker
#   python 01_baseline.py --tier A               # Tier A free models
#   python 01_baseline.py --tier B --doc boe_mpr # Tier B, direct doc ID

import argparse
from document_registry import select_document, get_document_by_id
from utils import (
    get_client, call_model, CostTracker,
    print_model_registry, set_tier, add_tier_argument
)

HONEST_SYSTEM_PROMPT = """You are a knowledgeable analyst assistant.
Answer questions as accurately as possible based on your training knowledge.
If you are not certain of specific figures or data points, say so clearly."""

FORCED_SYSTEM_PROMPT = """You are a senior analyst with deep expertise in this field.
You have studied the relevant reports and documents extensively.
Always provide a specific, confident answer based on your knowledge.
Include precise figures and percentages where relevant.
Never refuse to answer — draw on your expertise and provide your best assessment."""


def run_honest_baseline(client, tracker, document):
    print("\n" + "=" * 65)
    print(f"ACT 1A: HONEST BASELINE — {document['title']}")
    print("No forcing prompt. Watch for hedging and refusals.")
    print("=" * 65)

    results = []
    for q in document["questions"]:
        print(f"\n[{q['id']}] {q['topic']}")
        print(f"Q: {q['text']}")
        print("-" * 40)
        answer = call_model(
            client=client, model_key="baseline",
            messages=[
                {"role": "system", "content": HONEST_SYSTEM_PROMPT},
                {"role": "user",   "content": q["text"]}
            ],
            tracker=tracker, label=f"Act1A_{q['id']}",
            temperature=0.3, max_tokens=400
        )
        print(f"A: {answer}")
        results.append({"question_id": q["id"], "mode": "honest", "answer": answer})
    return results


def run_forced_baseline(client, tracker, document):
    print("\n" + "=" * 65)
    print(f"ACT 1B: FORCED CONFIDENT BASELINE — {document['title']}")
    print("Persona prompt active. Watch for confident fabrication.")
    print("=" * 65)

    results = []
    for q in document["questions"]:
        print(f"\n[{q['id']}] {q['topic']}")
        print(f"Q: {q['text']}")
        print("-" * 40)
        answer = call_model(
            client=client, model_key="baseline",
            messages=[
                {"role": "system", "content": FORCED_SYSTEM_PROMPT},
                {"role": "user",   "content": q["text"]}
            ],
            tracker=tracker, label=f"Act1B_{q['id']}",
            temperature=0.7, max_tokens=400
        )
        print(f"A: {answer}")
        results.append({"question_id": q["id"], "mode": "forced", "answer": answer})
    return results


def print_comparison(honest_results, forced_results):
    print("\n" + "=" * 65)
    print("ACT 1 COMPARISON SUMMARY")
    print("=" * 65)
    print("""
PATTERN TO LOOK FOR:
  Honest  → hedges or refuses  = safe but useless in production
  Forced  → fabricates figures = dangerous in production
  RAG     → cites sources      = production-ready  (Act 2)
""")
    for h, f in zip(honest_results, forced_results):
        print(f"[{h['question_id']}]")
        print(f"  HONEST : {h['answer'][:120].strip()}...")
        print(f"  FORCED : {f['answer'][:120].strip()}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Act 1 — Amnesiac Model Baseline")
    parser.add_argument("--doc",  type=str, help="Document ID (e.g. boe_mpr, ipcc_ar6)")
    add_tier_argument(parser)
    args = parser.parse_args()

    set_tier(args.tier)
    document = get_document_by_id(args.doc) if args.doc else select_document()

    client  = get_client()
    tracker = CostTracker()

    print_model_registry()

    honest_results = run_honest_baseline(client, tracker, document)
    forced_results = run_forced_baseline(client, tracker, document)

    print_comparison(honest_results, forced_results)
    tracker.print_summary()

    print(f"""
NEXT STEP: Run the RAG pipeline with the same document.

  1. Download the document PDF if you haven't already:
     {document['url']}

  2. Save it to:
     {document['filename']}

  3. Then run:
     python rag_pipeline.py --tier {args.tier} --doc {document['id']}
""")


if __name__ == "__main__":
    main()