# 02_rag_pipeline.py — Act 2: The Clean RAG Pipeline
#
# Build sequence:
#   Step 1 — Ingest:    Extract text from PDF using pdfplumber
#   Step 2 — Chunk:     Split into overlapping chunks, show one as example
#   Step 3 — Embed:     Convert chunks to embeddings via OpenRouter
#   Step 4 — Store:     Persist in ChromaDB locally
#   Step 5 — Retrieve:  Find closest chunks for each question
#   Step 6 — Generate:  Answer with retrieved context + citations
#
# Same three questions as Act 1.
# Compare outputs directly — same questions, grounded answers.

import os
import json
import pdfplumber
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from utils import get_client, call_model, CostTracker, QUESTIONS, print_model_registry, MODEL_REGISTRY

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

PDF_PATH       = "documents/boe_mpr_feb2025.pdf"
CHROMA_PATH    = "./chroma_db"
COLLECTION     = "boe_mpr_feb2025"
CHUNK_SIZE     = 500       # characters per chunk
CHUNK_OVERLAP  = 100       # overlap between chunks
TOP_K          = 4         # chunks to retrieve per query
EMBED_MODEL    = "text-embedding-3-small"   # via OpenRouter

# ── Step 1: PDF Ingestion ──────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text page by page.
    Returns list of {page_num, text} dicts.
    Preserves page numbers for citation purposes.
    """
    print("\n" + "=" * 65)
    print("STEP 1: PDF INGESTION")
    print("=" * 65)

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Document: {pdf_path}")
        print(f"Pages found: {total}")

        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({
                    "page_num": i + 1,
                    "text":     text.strip()
                })

    print(f"Pages with extractable text: {len(pages)}")
    return pages


# ── Step 2: Chunking ───────────────────────────────────────────────────────────

def chunk_pages(pages: list[dict], chunk_size: int, overlap: int) -> list[dict]:
    """
    Split page text into overlapping chunks.
    Each chunk retains page_num for citation.
    Shows one example chunk so the process is visible.
    """
    print("\n" + "=" * 65)
    print("STEP 2: CHUNKING")
    print("=" * 65)

    chunks = []
    chunk_id = 0

    for page in pages:
        text = page["text"]
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "id":       f"chunk_{chunk_id:04d}",
                    "text":     chunk_text,
                    "page_num": page["page_num"],
                    "start":    start
                })
                chunk_id += 1

            start += chunk_size - overlap

    print(f"Chunk size:    {chunk_size} characters")
    print(f"Chunk overlap: {overlap} characters")
    print(f"Total chunks:  {len(chunks)}")

    # Show one example chunk — demystifies what the model actually sees
    if chunks:
        example = chunks[min(10, len(chunks) - 1)]
        print(f"\nEXAMPLE CHUNK [{example['id']} | Page {example['page_num']}]:")
        print("-" * 40)
        print(example["text"])
        print("-" * 40)
        print("^ This is what the model retrieves and reasons over.")

    return chunks


# ── Step 3 & 4: Embed and Store ────────────────────────────────────────────────

def get_embedding_client() -> OpenAI:
    """Embedding client — uses OpenAI embeddings via OpenRouter."""
    return OpenAI(
        api_key  = os.getenv("OPENROUTER_API_KEY"),
        base_url = "https://openrouter.ai/api/v1",
        default_headers = {
            "HTTP-Referer": "https://ainavigatorhq.substack.com",
            "X-Title":      "AI Navigator RAG Lab W9",
        }
    )


def embed_and_store(chunks: list[dict], tracker: CostTracker) -> chromadb.Collection:
    """
    Embed all chunks and store in ChromaDB.
    Skips re-embedding if collection already exists.
    Returns the ChromaDB collection.
    """
    print("\n" + "=" * 65)
    print("STEP 3 & 4: EMBEDDING AND VECTOR STORE")
    print("=" * 65)

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Check if collection already built
    existing = [c.name for c in chroma_client.list_collections()]
    if COLLECTION in existing:
        print(f"Collection '{COLLECTION}' already exists — loading from disk.")
        print("Delete ./chroma_db to force re-embedding.")
        return chroma_client.get_collection(COLLECTION)

    print(f"Building new collection: '{COLLECTION}'")
    print(f"Embedding model: {EMBED_MODEL}")
    print(f"Embedding {len(chunks)} chunks via OpenRouter...")

    embed_client = get_embedding_client()
    collection   = chroma_client.create_collection(COLLECTION)

    # Embed in batches of 50 to avoid rate limits
    batch_size  = 50
    total_tokens = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]

        response = embed_client.embeddings.create(
            model = EMBED_MODEL,
            input = texts
        )

        embeddings = [r.embedding for r in response.data]
        total_tokens += response.usage.total_tokens

        collection.add(
            ids        = [c["id"] for c in batch],
            embeddings = embeddings,
            documents  = [c["text"] for c in batch],
            metadatas  = [{"page_num": c["page_num"]} for c in batch]
        )

        print(f"  Embedded chunks {i+1}–{min(i+batch_size, len(chunks))} of {len(chunks)}")

    # Log embedding cost
    # text-embedding-3-small: $0.02 / 1M tokens via OpenAI
    embed_cost = total_tokens * 0.00000002
    print(f"\nTotal embedding tokens: {total_tokens:,}")
    print(f"Embedding cost:         ${embed_cost:.6f}")

    tracker.sessions.append({
        "label":             "Embedding",
        "model_name":        EMBED_MODEL,
        "prompt_tokens":     total_tokens,
        "completion_tokens": 0,
        "input_cost":        embed_cost,
        "output_cost":       0.0,
        "total_cost":        embed_cost
    })

    print(f"\nVector store saved to: {CHROMA_PATH}")
    return collection


# ── Step 5: Retrieval ──────────────────────────────────────────────────────────

def retrieve_chunks(
    query: str,
    collection: chromadb.Collection,
    embed_client: OpenAI,
    top_k: int = TOP_K
) -> list[dict]:
    """
    Embed the query and retrieve top_k closest chunks.
    Returns list of {text, page_num, distance} dicts.
    """
    response = embed_client.embeddings.create(
        model = EMBED_MODEL,
        input = [query]
    )
    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = top_k,
        include          = ["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "text":     doc,
            "page_num": meta["page_num"],
            "distance": round(dist, 4)
        })

    return chunks


# ── Step 6: Generation ─────────────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are a financial analyst assistant with access to 
specific excerpts from the Bank of England Monetary Policy Report, February 2025.

Answer questions using ONLY the provided context excerpts.
Always cite the specific page number(s) you drew from.
If the context does not contain enough information to answer precisely, say so.
Never fabricate figures or data not present in the context."""


def build_rag_prompt(question: str, retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks as numbered context for the model."""
    context_blocks = []

    for i, chunk in enumerate(retrieved_chunks, 1):
        context_blocks.append(
            f"[Source {i} — Page {chunk['page_num']} "
            f"| Similarity distance: {chunk['distance']}]\n"
            f"{chunk['text']}"
        )

    context = "\n\n".join(context_blocks)

    return f"""CONTEXT FROM DOCUMENT:
{context}

QUESTION:
{question}

Answer using only the context above. Cite page numbers."""


def run_rag_pipeline(client, embed_client, collection, tracker):
    print("\n" + "=" * 65)
    print("STEP 5 & 6: RETRIEVAL + GENERATION")
    print("Same questions as Act 1. Grounded answers with citations.")
    print("=" * 65)

    results = []

    for q in QUESTIONS:
        print(f"\n[{q['id']}] {q['topic']}")
        print(f"Q: {q['text']}")
        print("-" * 40)

        # Retrieve
        chunks = retrieve_chunks(q["text"], collection, embed_client)

        print(f"Retrieved {len(chunks)} chunks:")
        for i, c in enumerate(chunks, 1):
            print(f"  Source {i}: Page {c['page_num']} | Distance: {c['distance']}")

        print()

        # Generate
        rag_prompt = build_rag_prompt(q["text"], chunks)

        answer = call_model(
            client      = client,
            model_key   = "rag",
            messages    = [
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user",   "content": rag_prompt}
            ],
            tracker     = tracker,
            label       = f"Act2_RAG_{q['id']}",
            temperature = 0.1,    # low temp for factual grounded answers
            max_tokens  = 600
        )

        print(f"A: {answer}")

        results.append({
            "question_id":      q["id"],
            "question":         q["text"],
            "retrieved_chunks": chunks,
            "answer":           answer
        })

    return results


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    client       = get_client()
    embed_client = get_embedding_client()
    tracker      = CostTracker()

    print_model_registry()

    # Step 1: Ingest
    pages = extract_text_from_pdf(PDF_PATH)

    # Step 2: Chunk
    chunks = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)

    # Steps 3 & 4: Embed and store
    collection = embed_and_store(chunks, tracker)

    # Steps 5 & 6: Retrieve and generate
    results = run_rag_pipeline(client, embed_client, collection, tracker)

    # Save results for Act 3 stress tests
    with open("act2_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to act2_results.json")

    tracker.print_summary()

    print("\nNEXT: Run 03_stress_tests.py to probe the failure modes.")


if __name__ == "__main__":
    main()