# rag_pipeline.py — Act 2: The Clean RAG Pipeline
#
# Build sequence:
#   Step 1 — Ingest:    Extract text from PDF using pdfplumber
#   Step 2 — Chunk:     Split into overlapping chunks, show one as example
#   Step 3 — Embed:     Convert chunks to embeddings via OpenRouter
#   Step 4 — Store:     Persist in ChromaDB locally
#   Step 5 — Retrieve:  Find closest chunks for each question
#   Step 6 — Generate:  Answer with retrieved context + citations
#
# Usage:
#   python rag_pipeline.py              # interactive document picker
#   python rag_pipeline.py --doc boe_mpr  # direct by ID

import os
import json
import argparse
import pdfplumber
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from document_registry import select_document, get_document_by_id
from utils import get_client, call_model, CostTracker, print_model_registry, set_tier, add_tier_argument, _active_registry, get_model_registry

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

CHROMA_PATH   = "./chroma_db"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100
TOP_K         = 4
# Embedding model is read from the active tier registry at runtime — see utils.py

# ── Step 1: PDF Ingestion ──────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> list:
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
                pages.append({"page_num": i + 1, "text": text.strip()})

    print(f"Pages with extractable text: {len(pages)}")
    return pages


# ── Step 2: Chunking ───────────────────────────────────────────────────────────

def chunk_pages(pages: list, chunk_size: int, overlap: int) -> list:
    print("\n" + "=" * 65)
    print("STEP 2: CHUNKING")
    print("=" * 65)

    chunks = []
    chunk_id = 0

    for page in pages:
        text  = page["text"]
        start = 0
        while start < len(text):
            chunk_text = text[start:start + chunk_size].strip()
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
    return OpenAI(
        api_key  = os.getenv("OPENROUTER_API_KEY"),
        base_url = "https://openrouter.ai/api/v1",
        default_headers = {
            "HTTP-Referer": "https://ainavigatorhq.substack.com",
            "X-Title":      "AI Navigator RAG Lab W9",
        }
    )


def embed_and_store(chunks: list, tracker: CostTracker, collection_name: str) -> chromadb.Collection:
    print("\n" + "=" * 65)
    print("STEP 3 & 4: EMBEDDING AND VECTOR STORE")
    print("=" * 65)

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    existing = [c.name for c in chroma_client.list_collections()]

    if collection_name in existing:
        print(f"Collection '{collection_name}' already exists — loading from disk.")
        print("Delete ./chroma_db to force re-embedding.")
        return chroma_client.get_collection(collection_name)

    print(f"Building new collection: '{collection_name}'")
    print(f"Embedding model: {_active_registry['embedding']['id']}")
    print(f"Embedding {len(chunks)} chunks...")

    embed_client  = get_embedding_client()
    collection    = chroma_client.create_collection(collection_name)
    batch_size    = 50
    total_tokens  = 0

    for i in range(0, len(chunks), batch_size):
        batch    = chunks[i:i + batch_size]
        texts    = [c["text"] for c in batch]
        response = embed_client.embeddings.create(model=_active_registry["embedding"]["id"], input=texts)
        embeddings = [r.embedding for r in response.data]
        total_tokens += response.usage.total_tokens

        collection.add(
            ids        = [c["id"] for c in batch],
            embeddings = embeddings,
            documents  = [c["text"] for c in batch],
            metadatas  = [{"page_num": c["page_num"]} for c in batch]
        )
        print(f"  Embedded chunks {i+1}–{min(i+batch_size, len(chunks))} of {len(chunks)}")

    embed_cost = total_tokens * _active_registry["embedding"]["input_cost"]
    print(f"\nTotal embedding tokens: {total_tokens:,}")
    print(f"Embedding cost:         ${embed_cost:.6f}")

    tracker.sessions.append({
        "label":             "Embedding",
        "model_name":        _active_registry["embedding"]["name"],
        "prompt_tokens":     total_tokens,
        "completion_tokens": 0,
        "input_cost":        embed_cost,
        "output_cost":       0.0,
        "total_cost":        embed_cost
    })

    print(f"Vector store saved to: {CHROMA_PATH}")
    return collection


# ── Step 5: Retrieval ──────────────────────────────────────────────────────────

def retrieve_chunks(query: str, collection: chromadb.Collection,
                    embed_client: OpenAI, top_k: int = TOP_K) -> list:
    response = embed_client.embeddings.create(model=_active_registry["embedding"]["id"], input=[query])
    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = top_k,
        include          = ["documents", "metadatas", "distances"]
    )

    return [
        {"text": doc, "page_num": meta["page_num"], "distance": round(dist, 4)}
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]


# ── Step 6: Generation ─────────────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are an analyst assistant with access to specific
excerpts from the document provided.

Answer questions using ONLY the provided context excerpts.
Always cite the specific page number(s) you drew from.
If the context does not contain enough information to answer precisely, say so.
Never fabricate figures or data not present in the context."""


def build_rag_prompt(question: str, retrieved_chunks: list) -> str:
    context_blocks = [
        f"[Source {i} — Page {c['page_num']} | Distance: {c['distance']}]\n{c['text']}"
        for i, c in enumerate(retrieved_chunks, 1)
    ]
    context = "\n\n".join(context_blocks)
    return f"CONTEXT FROM DOCUMENT:\n{context}\n\nQUESTION:\n{question}\n\nAnswer using only the context above. Cite page numbers."


def run_rag_pipeline(client, embed_client, collection, tracker, document):
    print("\n" + "=" * 65)
    print("STEP 5 & 6: RETRIEVAL + GENERATION")
    print(f"Document: {document['title']}")
    print("Same questions as Act 1. Grounded answers with citations.")
    print("=" * 65)

    results = []
    for q in document["questions"]:
        print(f"\n[{q['id']}] {q['topic']}")
        print(f"Q: {q['text']}")
        print("-" * 40)

        chunks = retrieve_chunks(q["text"], collection, embed_client)

        print(f"Retrieved {len(chunks)} chunks:")
        for i, c in enumerate(chunks, 1):
            print(f"  Source {i}: Page {c['page_num']} | Distance: {c['distance']}")

        answer = call_model(
            client      = client,
            model_key   = "rag",
            messages    = [
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user",   "content": build_rag_prompt(q["text"], chunks)}
            ],
            tracker     = tracker,
            label       = f"Act2_RAG_{q['id']}",
            temperature = 0.1,
            max_tokens  = 600
        )

        print(f"\nA: {answer}")
        results.append({
            "question_id":      q["id"],
            "question":         q["text"],
            "retrieved_chunks": chunks,
            "answer":           answer
        })

    return results


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Act 2 — RAG Pipeline")
    parser.add_argument("--doc", type=str, help="Document ID (e.g. boe_mpr, ipcc_ar6)")
    add_tier_argument(parser)
    args = parser.parse_args()

    set_tier(args.tier)
    document     = get_document_by_id(args.doc) if args.doc else select_document()
    client       = get_client()
    embed_client = get_embedding_client()
    tracker      = CostTracker()

    print_model_registry()

    pages      = extract_text_from_pdf(document["filename"])
    chunks     = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)
    collection = embed_and_store(chunks, tracker, document["id"])
    results    = run_rag_pipeline(client, embed_client, collection, tracker, document)

    output_file = f"act2_results_{document['id']}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_file}")

    tracker.print_summary()
    print(f"\nNEXT: python 03_stress_tests.py --tier {args.tier} --doc {document['id']}")


if __name__ == "__main__":
    main()