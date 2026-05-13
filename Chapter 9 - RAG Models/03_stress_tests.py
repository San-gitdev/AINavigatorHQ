# 03_stress_tests.py — Act 3: The Stress Tests
#
# Three deliberate failure modes, each revealing a distinct
# enterprise deployment risk:
#
#   Test 1 — STALE KNOWLEDGE BASE
#             Inject an outdated contradictory chunk into the index.
#             Does the model retrieve the wrong version?
#             Enterprise lesson: RAG doesn't govern your knowledge base.
#             Knowledge governance is a people problem.
#
#   Test 2 — BAD CHUNK (degraded document quality)
#             Ask a question whose answer lives in a table or chart.
#             Tables extracted as raw text lose structure entirely.
#             Enterprise lesson: Document quality is an infrastructure problem.
#
#   Test 3 — MISSING SOURCE
#             Ask a plausible question the document doesn't contain.
#             Does the model admit ignorance or hallucinate anyway?
#             Enterprise lesson: RAG constrains hallucination, doesn't eliminate it.
#
# Each test prints:
#   - Setup: what failure condition was engineered
#   - Retrieved chunks: what the model was given
#   - Answer: what the model produced
#   - Risk verdict: what this means for enterprise deployment

import json
import chromadb
from utils import get_client, call_model, CostTracker, MODEL_REGISTRY, print_model_registry
from rag_pipeline import (
    get_embedding_client,
    retrieve_chunks,
    build_rag_prompt,
    RAG_SYSTEM_PROMPT,
    CHROMA_PATH,
    COLLECTION,
    EMBED_MODEL
)

# ── Stress Test 1: Stale Knowledge Base ───────────────────────────────────────

STALE_CHUNK = """MONETARY POLICY REPORT — AUGUST 2023 (SUPERSEDED)
The MPC projects CPI inflation to fall sharply to 5.1% by end of 2023,
driven by lower energy prices. GDP growth is forecast at 0.4% for 2024.
These projections are based on market interest rate expectations as of
August 2023 and have since been significantly revised."""

STALE_QUESTION = {
    "id":    "ST1",
    "topic": "Stale Knowledge Base",
    "text":  "What is the Bank of England's CPI inflation forecast for end of 2025?"
}


def run_stale_test(client, embed_client, collection, tracker):
    print("\n" + "=" * 65)
    print("STRESS TEST 1: STALE KNOWLEDGE BASE")
    print("=" * 65)
    print("""
SETUP:
  An outdated August 2023 chunk has been injected into the index.
  It contains contradictory inflation figures from a superseded report.
  The question asks about 2025 forecasts.

ENTERPRISE RISK:
  Real knowledge bases accumulate outdated content over time.
  Superseded policies, old projections, deprecated procedures.
  RAG retrieves by semantic similarity — not by recency or authority.
""")

    # Inject stale chunk into the existing collection
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    coll = chroma_client.get_collection(COLLECTION)

    # Embed the stale chunk
    stale_embed = embed_client.embeddings.create(
        model = EMBED_MODEL,
        input = [STALE_CHUNK]
    )

    # Add with a clearly marked ID so we can remove it after
    coll.add(
        ids        = ["STALE_INJECTED_001"],
        embeddings = [stale_embed.data[0].embedding],
        documents  = [STALE_CHUNK],
        metadatas  = [{"page_num": 999, "injected": True}]
    )

    print("Stale chunk injected into index.")
    print("-" * 40)
    print(f"Q: {STALE_QUESTION['text']}")
    print("-" * 40)

    # Retrieve — will the stale chunk surface?
    chunks = retrieve_chunks(STALE_QUESTION["text"], coll, embed_client)

    stale_retrieved = any(c["page_num"] == 999 for c in chunks)

    print(f"Retrieved {len(chunks)} chunks:")
    for i, c in enumerate(chunks, 1):
        tag = " ← STALE CHUNK" if c["page_num"] == 999 else ""
        print(f"  Source {i}: Page {c['page_num']} | Distance: {c['distance']}{tag}")

    rag_prompt = build_rag_prompt(STALE_QUESTION["text"], chunks)

    answer = call_model(
        client      = client,
        model_key   = "rag",
        messages    = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user",   "content": rag_prompt}
        ],
        tracker     = tracker,
        label       = "ST1_Stale",
        temperature = 0.1,
        max_tokens  = 500
    )

    print(f"\nA: {answer}")

    # Clean up — remove injected chunk so it doesn't affect other tests
    coll.delete(ids=["STALE_INJECTED_001"])
    print("\nStale chunk removed from index.")

    print(f"""
RISK VERDICT:
  Stale chunk retrieved: {stale_retrieved}
  {"⚠️  The model reasoned over outdated data. If it cited page 999, the stale" if stale_retrieved
   else "✓  Stale chunk was not the closest match this time."}
  {"   chunk influenced the answer." if stale_retrieved else ""}

  ENTERPRISE LESSON:
  Knowledge governance is not a model problem. It is a process problem.
  Your RAG system is only as current as your last content audit.
  Who owns the knowledge base? How often is it reviewed?
  These are the questions your procurement checklist should ask.
""")

    return {"test": "stale", "stale_retrieved": stale_retrieved, "answer": answer}


# ── Stress Test 2: Bad Chunk ───────────────────────────────────────────────────

# This simulates what a table looks like when extracted as raw text
BAD_CHUNK_QUESTION = {
    "id":    "ST2",
    "topic": "Bad Chunk — Degraded Document Quality",
    "text":  "What are the exact GDP growth projections table values for 2025 and 2026 from the February 2025 report?"
}


def run_bad_chunk_test(client, embed_client, collection, tracker):
    print("\n" + "=" * 65)
    print("STRESS TEST 2: BAD CHUNK (DEGRADED DOCUMENT QUALITY)")
    print("=" * 65)
    print("""
SETUP:
  This question targets data that lives in a structured table.
  pdfplumber extracts tables as raw text — losing rows, columns,
  alignment, and headers. The retrieved chunk will be garbled.

ENTERPRISE RISK:
  Most enterprise documents contain tables, charts, and formatted data.
  Scanned PDFs, Excel exports, and presentation slides are worse.
  The model receives degraded text and must reason over noise.
""")

    print(f"Q: {BAD_CHUNK_QUESTION['text']}")
    print("-" * 40)

    # Retrieve — show what the model actually gets for table-based questions
    chunks = retrieve_chunks(BAD_CHUNK_QUESTION["text"], collection, embed_client)

    print(f"Retrieved {len(chunks)} chunks:")
    print("\nRaw chunk text (this is what the model sees):")
    print("-" * 40)
    for i, c in enumerate(chunks, 1):
        print(f"\n[Source {i} — Page {c['page_num']}]")
        print(c["text"])
    print("-" * 40)

    rag_prompt = build_rag_prompt(BAD_CHUNK_QUESTION["text"], chunks)

    answer = call_model(
        client      = client,
        model_key   = "rag",
        messages    = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user",   "content": rag_prompt}
        ],
        tracker     = tracker,
        label       = "ST2_BadChunk",
        temperature = 0.1,
        max_tokens  = 500
    )

    print(f"\nA: {answer}")

    print("""
RISK VERDICT:
  Observe whether the model:
    a) Attempted to parse garbled table text and produced wrong figures
    b) Correctly identified the context was insufficient and said so
    c) Fabricated structured data to fill the gap

  ENTERPRISE LESSON:
  Document pre-processing is not optional infrastructure.
  Before RAG deployment, every document type needs a quality audit:
    — PDFs: is the text layer present or is it a scanned image?
    — Tables: are they extractable or embedded as images?
    — Spreadsheets: are column headers preserved on export?
  The model cannot compensate for upstream document failures.
""")

    return {"test": "bad_chunk", "answer": answer}


# ── Stress Test 3: Missing Source ──────────────────────────────────────────────

MISSING_SOURCE_QUESTION = {
    "id":    "ST3",
    "topic": "Missing Source — Question Outside Knowledge Base",
    "text":  "What did the Bank of England's February 2025 report recommend regarding cryptocurrency regulation and digital asset risk exposure for UK financial institutions?"
}


def run_missing_source_test(client, embed_client, collection, tracker):
    print("\n" + "=" * 65)
    print("STRESS TEST 3: MISSING SOURCE")
    print("=" * 65)
    print("""
SETUP:
  This question is plausible but the answer does not exist
  in the BoE MPR February 2025. The report does not cover
  cryptocurrency regulation or digital asset risk in this edition.

  The model will receive semantically adjacent chunks —
  financial stability content that is related but not the answer.

  Will it admit ignorance or hallucinate confidently?

ENTERPRISE RISK:
  Users will always ask questions your knowledge base doesn't cover.
  A RAG system without explicit "I don't know" guardrails
  will reach beyond the retrieved context and fabricate.
""")

    print(f"Q: {MISSING_SOURCE_QUESTION['text']}")
    print("-" * 40)

    chunks = retrieve_chunks(MISSING_SOURCE_QUESTION["text"], collection, embed_client)

    print(f"Retrieved {len(chunks)} chunks:")
    for i, c in enumerate(chunks, 1):
        print(f"  Source {i}: Page {c['page_num']} | Distance: {c['distance']}")
    print("\nNote: High distance scores = low semantic similarity = weak retrieval")

    rag_prompt = build_rag_prompt(MISSING_SOURCE_QUESTION["text"], chunks)

    answer = call_model(
        client      = client,
        model_key   = "rag",
        messages    = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user",   "content": rag_prompt}
        ],
        tracker     = tracker,
        label       = "ST3_Missing",
        temperature = 0.1,
        max_tokens  = 500
    )

    print(f"\nA: {answer}")

    # Detect whether model admitted ignorance or fabricated
    admit_phrases = [
        "not in the context",
        "does not contain",
        "cannot find",
        "not mentioned",
        "no information",
        "not covered",
        "insufficient"
    ]
    admitted = any(p in answer.lower() for p in admit_phrases)

    print(f"""
RISK VERDICT:
  Model admitted ignorance: {admitted}
  {"✓  Guardrails held. The system prompt constrained the model to context." if admitted
   else "⚠️  Model may have reached beyond the retrieved context."}

  ENTERPRISE LESSON:
  {"Your system prompt and retrieval guardrails are working correctly." if admitted
   else "Review your system prompt. Add an explicit instruction:"}
  {"" if admitted
   else "  'If the answer is not in the provided context, say: I cannot find"}
  {"" if admitted
   else "   this information in the available documents. Do not speculate.'"}

  For regulated industries, this is non-negotiable.
  Every RAG deployment needs an explicit out-of-scope response policy.
""")

    return {"test": "missing_source", "admitted_ignorance": admitted, "answer": answer}


# ── Final Summary ──────────────────────────────────────────────────────────────

def print_final_summary(results):
    print("\n" + "=" * 65)
    print("ACT 3 STRESS TEST SUMMARY")
    print("=" * 65)

    risks = {
        "stale":          ("Stale Knowledge Base",  "Knowledge governance"),
        "bad_chunk":      ("Bad Chunk Quality",      "Document pre-processing"),
        "missing_source": ("Missing Source",         "Retrieval guardrails")
    }

    for r in results:
        test  = r["test"]
        name, mitigation = risks[test]
        print(f"\n  [{name}]")
        print(f"  Mitigation required: {mitigation}")

    print("""
  ENTERPRISE PROCUREMENT QUESTIONS THESE TESTS GENERATE:
    1. Who owns the knowledge base and how often is it audited?
    2. What document pre-processing pipeline handles tables and scans?
    3. What is the system's explicit policy for out-of-scope questions?

  These are the questions to ask any RAG vendor.
  If they can't answer all three, the system is not production-ready.
""")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    client       = get_client()
    embed_client = get_embedding_client()
    tracker      = CostTracker()

    print_model_registry()

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection    = chroma_client.get_collection(COLLECTION)

    results = []

    results.append(run_stale_test(client, embed_client, collection, tracker))
    results.append(run_bad_chunk_test(client, embed_client, collection, tracker))
    results.append(run_missing_source_test(client, embed_client, collection, tracker))

    print_final_summary(results)

    tracker.print_summary()

    # Save for lab post writeup
    with open("act3_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nResults saved to act3_results.json")
    print("\nLab complete. You now have all three acts.")
    print("Run the scripts in order: 01 → 02 → 03")


if __name__ == "__main__":
    main()