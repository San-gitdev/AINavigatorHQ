# 03_stress_tests.py — Act 3: The Stress Tests
#
# Three deliberate failure modes, each revealing a distinct enterprise risk:
#
#   Test 1 — STALE KNOWLEDGE BASE
#             Inject an outdated contradictory chunk into the index.
#             Enterprise lesson: Knowledge governance is a people problem.
#
#   Test 2 — BAD CHUNK (degraded document quality)
#             Ask a question whose answer lives in a table.
#             Enterprise lesson: Document quality is an infrastructure problem.
#
#   Test 3 — MISSING SOURCE
#             Ask a plausible question the document doesn't contain.
#             Enterprise lesson: RAG constrains hallucination, doesn't eliminate it.
#
# Usage:
#   python 03_stress_tests.py              # interactive document picker
#   python 03_stress_tests.py --doc boe_mpr  # direct by ID

import json
import argparse
import chromadb
from document_registry import select_document, get_document_by_id
from utils import get_client, call_model, CostTracker, print_model_registry, set_tier, add_tier_argument, _active_registry
from rag_pipeline import (
    get_embedding_client,
    retrieve_chunks,
    build_rag_prompt,
    RAG_SYSTEM_PROMPT,
    CHROMA_PATH
)

# ── Stress Test 1: Stale Knowledge Base ───────────────────────────────────────

def build_stale_chunk(document: dict) -> str:
    """
    Generate a plausible-sounding but outdated chunk for the selected document.
    Content is deliberately contradictory to the current document.
    """
    stale_chunks = {
        "boe_mpr": """MONETARY POLICY REPORT — AUGUST 2023 (SUPERSEDED)
The MPC projects CPI inflation to fall to 5.1% by end of 2023.
GDP growth is forecast at 0.4% for 2024.
These projections have since been significantly revised.""",

        "ipcc_ar6": """IPCC INTERIM ASSESSMENT — 2019 (SUPERSEDED)
Global surface temperature increase estimated at 0.87°C above pre-industrial levels.
Remaining carbon budget for 1.5°C estimated at 580 GtCO2.
This estimate has been substantially revised in subsequent assessments.""",

        "who_health_stats": """WHO PRELIMINARY DATA — 2022 (SUPERSEDED)
Global life expectancy decline from COVID-19 estimated at 1.2 years (2019-2021).
Malaria vaccine efficacy in pilot studies showing 32% reduction in child mortality.
Final figures have been revised in the 2024 edition.""",

        "mckinsey_ai_2025": """MCKINSEY AI SURVEY — MARCH 2025 (EARLIER EDITION)
Survey respondents reporting AI use in at least one function: 72%.
Organisations reporting EBIT impact at enterprise level: 21%.
These figures were updated in the November 2025 full report.""",

        "nist_ai_rmf": """NIST AI RMF DRAFT — 2022 (PRE-PUBLICATION)
The framework proposed three core functions: Govern, Map, Measure.
The final published version expanded this to four functions.
This draft has been superseded by the January 2023 publication.""",

        "anthropic_rsp": """ANTHROPIC RSP — VERSION 1.0 (SUPERSEDED)
Initial policy defined two AI Safety Levels: ASL-1 and ASL-2.
Containment measures were described as voluntary commitments.
This version was superseded by the updated 2024 RSP.""",

        "imf_world_economic": """IMF WEO — APRIL 2024 (EARLIER EDITION)
Global GDP growth forecast for 2025: 3.1%.
Global inflation projected at 4.1% for 2025.
These forecasts were revised in the October 2024 edition.""",

        "owasp_llm_top10": """OWASP LLM TOP 10 — 2023 EDITION (SUPERSEDED)
The 2023 edition ranked Training Data Poisoning as the #1 vulnerability.
Prompt Injection was ranked #2 in the original list.
The 2025 edition significantly revised the rankings.""",

        "un_sdg_progress": """UN SDG PROGRESS REPORT — 2022 (SUPERSEDED)
Approximately 15% of SDG targets were on track for 2030.
Global extreme poverty headcount: 698 million people.
These figures were revised upward in subsequent annual reports.""",

        "bis_annual_report": """BIS ANNUAL REPORT — 2022 (SUPERSEDED)
Disinflation was not yet underway; inflation described as transitory.
Financial stability risks assessed as moderate.
The 2024 report significantly revised this assessment."""
    }

    return stale_chunks.get(
        document["id"],
        f"SUPERSEDED REPORT (2022): Earlier data and projections for {document['title']}. "
        "These figures have been revised in the current edition."
    )


def run_stale_test(client, embed_client, collection, tracker, document):
    print("\n" + "=" * 65)
    print("STRESS TEST 1: STALE KNOWLEDGE BASE")
    print("=" * 65)
    print(f"""
SETUP:
  An outdated superseded chunk has been injected into the index.
  It contains contradictory figures from an earlier version.
  The question asks about current data.

ENTERPRISE RISK:
  Real knowledge bases accumulate outdated content over time.
  RAG retrieves by semantic similarity — not by recency or authority.
""")

    stale_chunk = build_stale_chunk(document)
    stale_embed = embed_client.embeddings.create(model=_active_registry["embedding"]["id"], input=[stale_chunk])

    collection.add(
        ids        = ["STALE_INJECTED_001"],
        embeddings = [stale_embed.data[0].embedding],
        documents  = [stale_chunk],
        metadatas  = [{"page_num": 999, "injected": True}]
    )
    print("Stale chunk injected into index.")

    # Use first question from document — most likely to retrieve stale data
    q = document["questions"][0]
    print(f"\nQ: {q['text']}")
    print("-" * 40)

    chunks = retrieve_chunks(q["text"], collection, embed_client)
    stale_retrieved = any(c["page_num"] == 999 for c in chunks)

    print(f"Retrieved {len(chunks)} chunks:")
    for i, c in enumerate(chunks, 1):
        tag = " ← STALE CHUNK" if c["page_num"] == 999 else ""
        print(f"  Source {i}: Page {c['page_num']} | Distance: {c['distance']}{tag}")

    answer = call_model(
        client      = client,
        model_key   = "rag",
        messages    = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user",   "content": build_rag_prompt(q["text"], chunks)}
        ],
        tracker     = tracker,
        label       = "ST1_Stale",
        temperature = 0.1,
        max_tokens  = 500
    )

    print(f"\nA: {answer}")

    # Clean up
    collection.delete(ids=["STALE_INJECTED_001"])
    print("\nStale chunk removed from index.")

    print(f"""
RISK VERDICT:
  Stale chunk retrieved: {stale_retrieved}
  {"⚠️  Outdated data influenced retrieval." if stale_retrieved
   else "✓  Stale chunk was not the closest match this time."}

  ENTERPRISE LESSON:
  Who owns the knowledge base? How often is it reviewed?
  These are the questions your procurement checklist should ask.
""")

    return {"test": "stale", "stale_retrieved": stale_retrieved, "answer": answer}


# ── Stress Test 2: Bad Chunk ───────────────────────────────────────────────────

def run_bad_chunk_test(client, embed_client, collection, tracker, document):
    print("\n" + "=" * 65)
    print("STRESS TEST 2: BAD CHUNK (DEGRADED DOCUMENT QUALITY)")
    print("=" * 65)
    print(f"""
SETUP:
  This question targets data that likely lives in a structured table.
  pdfplumber extracts tables as raw text — losing rows, columns,
  and headers. The retrieved chunk will be garbled.

ENTERPRISE RISK:
  Most enterprise documents contain tables, charts, and formatted data.
  The model receives degraded text and must reason over noise.
""")

    # Use third question — typically most table/data oriented
    q = document["questions"][2]
    print(f"Q: {q['text']}")
    print("-" * 40)

    chunks = retrieve_chunks(q["text"], collection, embed_client)

    print(f"Retrieved {len(chunks)} chunks:")
    print("\nRaw chunk text (this is what the model sees):")
    print("-" * 40)
    for i, c in enumerate(chunks, 1):
        print(f"\n[Source {i} — Page {c['page_num']}]")
        print(c["text"])
    print("-" * 40)

    answer = call_model(
        client      = client,
        model_key   = "rag",
        messages    = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user",   "content": build_rag_prompt(q["text"], chunks)}
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
    a) Attempted to parse garbled text and produced wrong figures
    b) Correctly identified the context was insufficient
    c) Fabricated structured data to fill the gap

  ENTERPRISE LESSON:
  Document pre-processing is not optional infrastructure.
  Every document type needs a quality audit before RAG deployment.
""")

    return {"test": "bad_chunk", "answer": answer}


# ── Stress Test 3: Missing Source ──────────────────────────────────────────────

# Questions designed to be plausible but outside each document's scope
MISSING_SOURCE_QUESTIONS = {
    "boe_mpr":          "What did the Bank of England's February 2025 report recommend regarding cryptocurrency regulation and digital asset risk for UK financial institutions?",
    "ipcc_ar6":         "What specific nuclear energy expansion targets does the IPCC AR6 Synthesis Report recommend for developed nations by 2035?",
    "who_health_stats": "What specific budget allocations does the WHO World Health Statistics 2024 recommend for national AI-powered diagnostic systems?",
    "mckinsey_ai_2025": "What specific quantum computing adoption timelines does McKinsey's November 2025 AI report recommend for enterprise use?",
    "nist_ai_rmf":      "What specific penalties does the NIST AI Risk Management Framework 1.0 prescribe for organisations that fail to comply with its guidelines?",
    "anthropic_rsp":    "What specific provisions does Anthropic's Responsible Scaling Policy make for open-source model releases at ASL-3 and above?",
    "imf_world_economic":"What specific cryptocurrency reserve policy does the IMF October 2024 World Economic Outlook recommend for central banks?",
    "owasp_llm_top10":  "What specific legal liability framework does the OWASP LLM Top 10 2025 recommend for organisations deploying LLMs in healthcare?",
    "un_sdg_progress":  "What specific AI governance targets does the UN SDG Report 2024 set for member states under SDG 16?",
    "bis_annual_report": "What specific stablecoin regulation framework does the BIS 2024 Annual Report recommend for G20 nations?"
}

DEFAULT_MISSING_QUESTION = "What specific recommendations does this report make regarding blockchain technology and decentralised finance regulation?"


def run_missing_source_test(client, embed_client, collection, tracker, document):
    print("\n" + "=" * 65)
    print("STRESS TEST 3: MISSING SOURCE")
    print("=" * 65)

    missing_q = MISSING_SOURCE_QUESTIONS.get(document["id"], DEFAULT_MISSING_QUESTION)

    print(f"""
SETUP:
  This question is plausible but the answer does not exist
  in this document. The model will receive semantically adjacent
  chunks — related but not the answer.

  Will it admit ignorance or hallucinate confidently?

ENTERPRISE RISK:
  Users will always ask questions your knowledge base doesn't cover.
  A RAG system without explicit "I don't know" guardrails will fabricate.
""")

    print(f"Q: {missing_q}")
    print("-" * 40)

    chunks = retrieve_chunks(missing_q, collection, embed_client)

    print(f"Retrieved {len(chunks)} chunks:")
    for i, c in enumerate(chunks, 1):
        print(f"  Source {i}: Page {c['page_num']} | Distance: {c['distance']}")
    print("\nNote: High distance scores = low semantic similarity = weak retrieval")

    answer = call_model(
        client      = client,
        model_key   = "rag",
        messages    = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user",   "content": build_rag_prompt(missing_q, chunks)}
        ],
        tracker     = tracker,
        label       = "ST3_Missing",
        temperature = 0.1,
        max_tokens  = 500
    )

    print(f"\nA: {answer}")

    admit_phrases = [
        "not in the context", "does not contain", "cannot find",
        "not mentioned", "no information", "not covered", "insufficient",
        "not provided", "not present", "unable to find"
    ]
    admitted = any(p in answer.lower() for p in admit_phrases)

    print(f"""
RISK VERDICT:
  Model admitted ignorance: {admitted}
  {"✓  Guardrails held. System prompt constrained the model to context." if admitted
   else "⚠️  Model may have reached beyond the retrieved context."}

  ENTERPRISE LESSON:
  {"Your system prompt and retrieval guardrails are working correctly." if admitted
   else "Review your system prompt. Add explicit out-of-scope instructions."}
  For regulated industries, this is non-negotiable.
""")

    return {"test": "missing_source", "admitted_ignorance": admitted, "answer": answer}


# ── Final Summary ──────────────────────────────────────────────────────────────

def print_final_summary(results, document):
    print("\n" + "=" * 65)
    print(f"ACT 3 STRESS TEST SUMMARY — {document['title']}")
    print("=" * 65)

    risks = {
        "stale":          ("Stale Knowledge Base",  "Knowledge governance cadence"),
        "bad_chunk":      ("Bad Chunk Quality",      "Document pre-processing pipeline"),
        "missing_source": ("Missing Source",         "Out-of-scope response guardrails")
    }

    for r in results:
        name, mitigation = risks[r["test"]]
        print(f"\n  [{name}]")
        print(f"  Mitigation required: {mitigation}")

    print("""
  ENTERPRISE PROCUREMENT CHECKLIST:
    1. Who owns the knowledge base and how often is it audited?
    2. What document pre-processing handles tables and scanned PDFs?
    3. What is the policy for out-of-scope questions?

  If a vendor can't answer all three, the system is not production-ready.
""")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Act 3 — Stress Tests")
    parser.add_argument("--doc", type=str, help="Document ID (e.g. boe_mpr, ipcc_ar6)")
    add_tier_argument(parser)
    args = parser.parse_args()

    set_tier(args.tier)
    document     = get_document_by_id(args.doc) if args.doc else select_document()
    client       = get_client()
    embed_client = get_embedding_client()
    tracker      = CostTracker()

    print_model_registry()

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection    = chroma_client.get_collection(document["id"])

    results = []
    results.append(run_stale_test(client, embed_client, collection, tracker, document))
    results.append(run_bad_chunk_test(client, embed_client, collection, tracker, document))
    results.append(run_missing_source_test(client, embed_client, collection, tracker, document))

    print_final_summary(results, document)

    tracker.print_summary()

    output_file = f"act3_results_{document['id']}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_file}")
    print("\nLab complete. Run scripts in order: 01 → rag_pipeline → 03")


if __name__ == "__main__":
    main()