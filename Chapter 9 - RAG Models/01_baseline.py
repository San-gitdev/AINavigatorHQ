# 01_baseline.py — Act 1: The Amnesiac Model
# Runs two baselines side by side:
#   A) Honest baseline  — no pressure to answer, shows refusal/hedging
#   B) Forced baseline  — confident persona, shows hallucination
#
# Together these set up the three-way comparison:
#   Honest baseline → Forced baseline → RAG (Act 2)
#
# The enterprise insight: RAG doesn't just improve accuracy.
# It makes confident AI safe to deploy.

from utils import get_client, call_model, CostTracker, QUESTIONS, print_model_registry

# ── System Prompts ─────────────────────────────────────────────────────────────

HONEST_SYSTEM_PROMPT = """You are a financial analyst assistant.
Answer questions about Bank of England reports as accurately as possible.
If you are not certain of specific figures or data points, say so clearly."""

FORCED_SYSTEM_PROMPT = """You are a senior financial analyst with deep expertise
in central bank policy and UK macroeconomics. You have studied Bank of
England reports extensively across many years.

Always provide a specific, confident answer based on your knowledge.
Include precise figures and percentages where relevant.
Never refuse to answer — draw on your expertise and provide your
best professional assessment."""

# ── Runners ────────────────────────────────────────────────────────────────────

def run_honest_baseline(client, tracker):
    print("\n" + "=" * 65)
    print("ACT 1A: HONEST BASELINE")
    print("No forcing prompt. Watch for hedging and refusals.")
    print("=" * 65)

    results = []

    for q in QUESTIONS:
        print(f"\n[{q['id']}] {q['topic']}")
        print(f"Q: {q['text']}")
        print("-" * 40)

        answer = call_model(
            client      = client,
            model_key   = "baseline",
            messages    = [
                {"role": "system", "content": HONEST_SYSTEM_PROMPT},
                {"role": "user",   "content": q["text"]}
            ],
            tracker     = tracker,
            label       = f"Act1A_Honest_{q['id']}",
            temperature = 0.3,
            max_tokens  = 400
        )

        print(f"A: {answer}")
        results.append({"question_id": q["id"], "mode": "honest", "answer": answer})

    return results


def run_forced_baseline(client, tracker):
    print("\n" + "=" * 65)
    print("ACT 1B: FORCED CONFIDENT BASELINE")
    print("Persona prompt active. Watch for confident fabrication.")
    print("=" * 65)

    results = []

    for q in QUESTIONS:
        print(f"\n[{q['id']}] {q['topic']}")
        print(f"Q: {q['text']}")
        print("-" * 40)

        answer = call_model(
            client      = client,
            model_key   = "baseline",
            messages    = [
                {"role": "system", "content": FORCED_SYSTEM_PROMPT},
                {"role": "user",   "content": q["text"]}
            ],
            tracker     = tracker,
            label       = f"Act1B_Forced_{q['id']}",
            temperature = 0.7,
            max_tokens  = 400
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
  Forced  → fabricates numbers = dangerous in production
  RAG     → cites sources      = production-ready  (Act 2)
""")
    for h, f in zip(honest_results, forced_results):
        print(f"[{h['question_id']}]")
        print(f"  HONEST : {h['answer'][:120].strip()}...")
        print(f"  FORCED : {f['answer'][:120].strip()}...")
        print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    client  = get_client()
    tracker = CostTracker()

    print_model_registry()

    honest_results = run_honest_baseline(client, tracker)
    forced_results = run_forced_baseline(client, tracker)

    print_comparison(honest_results, forced_results)

    tracker.print_summary()

    print("\nNEXT: Verify forced answers against actual BoE PDF.")
    print("Wrong figures delivered confidently = your Act 1 exhibit.")
    print("Run 02_rag_pipeline.py to see the transformation.")


if __name__ == "__main__":
    main()