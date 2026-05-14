# AI Navigator — W9 RAG Lab
### *The New Memory Stack: Build, Break, and Understand RAG*

A hands-on lab built for [The AI Navigator](https://ainavigatorhq.substack.com) — Week 9.

You will build a Retrieval-Augmented Generation (RAG) pipeline from scratch, watch it work correctly, then deliberately break it in three ways that matter for enterprise deployment. No ML background required. Total cost per run: **free (Tier A) or under $0.05 (Tier B)**.

---

## What this lab does

The lab runs in three acts:

**Act 1 — The Amnesiac Model** (`01_baseline.py`)
Ask a raw language model questions about a document it has never seen. Run it twice — once with an honest prompt (watch it hedge), once with a confident persona (watch it fabricate specific figures). This is the "before."

**Act 2 — The RAG Pipeline** (`rag_pipeline.py`)
Build a working RAG system: ingest a PDF, chunk it, embed it into a local vector database, retrieve relevant passages, and generate grounded answers with page citations. Same questions as Act 1. This is the "after."

**Act 3 — The Stress Tests** (`03_stress_tests.py`)
Three deliberate failure modes that reveal enterprise deployment risks:
- Stale knowledge base — inject outdated contradictory content, watch what gets retrieved
- Bad chunk quality — ask a question whose answer lives in a table, watch retrieval break
- Missing source — ask a plausible question the document doesn't cover, watch whether the model admits ignorance or fabricates

---

## Architecture

```
YOUR MACHINE (client)                    REMOTE APIs (server)
─────────────────────────────            ──────────────────────────────
Python scripts                           OpenRouter
  01_baseline.py          ──queries──►     Tier A: free models
  rag_pipeline.py         ◄─responses─     Tier B: paid models
  03_stress_tests.py
                                         Embedding API
ChromaDB (local)          ◄─vectors──      text-embedding-3-small
  stores your chunks
  never leaves your machine

document_registry.py      ──chunks──►   ⚠ Privacy note: document chunks
  10 documents                          travel to the embedding API
  30 calibrated questions               on first indexing. Queries
                                        travel on every call. Your API
.env (API keys)                         keys stay local in .env and
  never committed to git                never leave your machine.

utils.py
  model registry
  cost tracker
  tier A/B switching
```

**What stays local:** your documents, your ChromaDB vector store, your API keys, all results JSON files.

**What leaves your machine:** document chunks (during embedding), query text (on every call), retrieved context (sent to the generation model).

---

## Setup

### Prerequisites
- Python 3.10 or higher
- An [OpenRouter](https://openrouter.ai) account with an API key
- Git

### 1. Clone the repository

```bash
git clone https://github.com/San-gitdev/AINavigatorHQ.git
cd "AINavigatorHQ/Chapter 9 - RAG Models"
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API keys

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Get your key at [openrouter.ai/keys](https://openrouter.ai/keys). No other keys required — all models route through OpenRouter.

> **Never commit your `.env` file.** It is already listed in `.gitignore`.

### 5. Download a document

Run the registry to see all available documents and their download URLs:

```bash
python document_registry.py
```

Download any document you want to use, save it to the `documents/` folder with the exact filename shown. Example:

```
documents/
  boe_mpr_feb2025.pdf
  anthropic_rsp_2024.pdf
  ipcc_ar6_syr_spm.pdf
```

---

## Running the lab

Run the three scripts in order. Each script accepts the same two arguments:

```
--tier A    free models, no credits needed (slower)
--tier B    paid models, <$0.05 per full run (faster, default)
--doc ID    document ID from the registry (interactive picker if omitted)
```

### Act 1 — Baseline

```bash
python 01_baseline.py --tier B --doc anthropic_rsp
```

If you omit `--doc`, an interactive menu appears letting you pick from all available documents.

**What to expect:** Two rounds of answers to the same three questions — one hedging/refusing, one confidently fabricating. Screenshot or copy the output before running Act 2.

### Act 2 — RAG Pipeline

```bash
python rag_pipeline.py --tier B --doc anthropic_rsp
```

**What to expect:** The script prints each build step — ingestion, chunking (with one example chunk shown), embedding progress, then retrieved chunks and grounded answers for each question. Results saved to `act2_results_[doc_id].json`.

> ChromaDB caches the vector store after the first run. Re-running Act 2 skips re-embedding and goes straight to retrieval. Delete the `chroma_db/` folder to force a fresh embed.

### Act 3 — Stress Tests

```bash
python 03_stress_tests.py --tier B --doc anthropic_rsp
```

**What to expect:** Three test outputs, each with a setup description, retrieved chunks (raw text shown for Test 2), a model answer, and a risk verdict. Results saved to `act3_results_[doc_id].json`.

---

## Available documents

| # | Title | Topic | Document ID |
|---|---|---|---|
| 1 | Bank of England — Monetary Policy Report, Feb 2025 | Finance / Central Banking | `boe_mpr` |
| 2 | IPCC — AR6 Synthesis Report: Climate Change 2023 | Climate / Environment | `ipcc_ar6` |
| 3 | WHO — World Health Statistics 2024 | Healthcare / Global Health | `who_health_stats` |
| 4 | McKinsey — State of AI 2025 (November) | Technology / AI Strategy | `mckinsey_ai_2025` |
| 5 | NIST — AI Risk Management Framework 1.0 | Governance / AI Risk | `nist_ai_rmf` |
| 6 | Anthropic — Responsible Scaling Policy (2024) | AI Safety / Policy | `anthropic_rsp` |
| 7 | IMF — World Economic Outlook, October 2024 | Economics / Global Markets | `imf_world_economic` |
| 8 | OWASP — Top 10 for LLM Applications 2025 | Cybersecurity / AI Risk | `owasp_llm_top10` |
| 9 | UN — Sustainable Development Goals Report 2024 | Policy / Global Development | `un_sdg_progress` |
| 10 | BIS — Annual Economic Report 2024 | Finance / Banking Regulation | `bis_annual_report` |

All documents are publicly available. Download URLs are printed when you run `python document_registry.py`.

---

## Model tiers

| | Tier A — Free | Tier B — Paid |
|---|---|---|
| **Cost** | $0.00 | <$0.05 per full run |
| **Baseline model** | Gemma 4 26B (free) | Mistral Small 4 |
| **RAG model** | NVIDIA Nemotron 3 Super (free) | Claude Sonnet 4.6 |
| **Stress test model** | Gemma 4 31B (free) | GPT-5.4 Nano |
| **Speed** | Slower (rate limited) | Faster |
| **Quality** | Good | Better |

Switch tiers at any point — add `--tier A` or `--tier B` to any script. The model registry and cost summary always print at the start of each run so you know exactly what's being used.

To change the default tier permanently, edit `DEFAULT_TIER` in `utils.py`:

```python
DEFAULT_TIER = "A"  # or "B"
```

---

## Configuration reference

### Chunking parameters (`rag_pipeline.py`)
```python
CHUNK_SIZE    = 500    # characters per chunk
CHUNK_OVERLAP = 100    # overlap between consecutive chunks
TOP_K         = 4      # chunks retrieved per query
```

Smaller chunks = more precise retrieval but less context per chunk. Larger chunks = more context but noisier retrieval. `TOP_K` controls how many chunks the model sees per question.

### Adding a new document (`document_registry.py`)
Add a new entry to `DOCUMENT_REGISTRY` following the existing pattern:

```python
"your_doc_id": {
    "id":          "your_doc_id",
    "title":       "Full Document Title",
    "filename":    "documents/your_file.pdf",
    "url":         "https://direct-pdf-url.com/file.pdf",
    "topic":       "Your Topic / Category",
    "description": "One line description",
    "questions": [
        {"id": "Q1", "topic": "Topic Name", "text": "Your question here?"},
        {"id": "Q2", "topic": "Topic Name", "text": "Your question here?"},
        {"id": "Q3", "topic": "Topic Name", "text": "Your question here?"}
    ]
}
```

Questions should be specific enough that the model cannot plausibly guess the answer from training data — named figures, specific dates, exact policy language.

---

## Project structure

```
w9_rag_lab/
├── .env                          # API keys — never commit this
├── .gitignore
├── requirements.txt
├── README.md
│
├── document_registry.py          # 10 documents, questions, download URLs
├── utils.py                      # model registry, cost tracker, tier switching
│
├── 01_baseline.py                # Act 1: amnesiac model (honest + forced)
├── rag_pipeline.py               # Act 2: full RAG build + retrieval + generation
├── 03_stress_tests.py            # Act 3: stale, bad chunk, missing source
│
├── documents/                    # put downloaded PDFs here
│   └── .gitkeep
│
└── chroma_db/                    # auto-created by ChromaDB on first embed
    └── (auto-generated)
```

---

## FAQ and troubleshooting

**`401 AuthenticationError` on first run**
Your OpenRouter API key is not being read correctly. Check:
- `.env` file exists in the project root (same folder as `utils.py`)
- Key has no quotes: `OPENROUTER_API_KEY=sk-or-v1-...` not `OPENROUTER_API_KEY="sk-or-v1-..."`
- Virtual environment is activated before running

**`FileNotFoundError: documents/your_file.pdf`**
The PDF has not been downloaded yet, or is saved with a different filename. Run `python document_registry.py` to see the exact expected filename for each document, then download and rename accordingly.

**`chromadb.errors.NotFoundError: Collection not found`**
Act 3 requires the ChromaDB collection to exist — meaning Act 2 must be run first for the same document. Run `rag_pipeline.py --doc your_doc_id` before `03_stress_tests.py --doc your_doc_id`.

**The model is hedging in Act 1B instead of hallucinating**
Some well-aligned models on OpenRouter refuse to fabricate even with a confident persona. Try a different Tier B baseline or raise temperature to 0.9 in `01_baseline.py`. The honest/forced contrast is the point — if both modes hedge, that's actually a valid finding worth noting.

**Embedding is slow / timing out**
Large documents with many chunks may hit OpenRouter rate limits during batch embedding. The script batches in groups of 50 — if it times out, reduce `batch_size` in `rag_pipeline.py` to 25 and re-run. Existing chunks already embedded are not re-sent.

**Re-running Act 2 re-embeds everything**
It shouldn't — ChromaDB checks for an existing collection by name and skips re-embedding if found. If you're seeing re-embedding, the collection name changed (e.g. you changed the document ID). Delete `chroma_db/` and re-run, or check the collection name matches `document["id"]`.

**Garbled text in the example chunk**
Some PDFs have encoding issues that cause pdfplumber to extract text without spaces (`ntsofthismagnitude` instead of `n ts of this magnitude`). This is a real-world document quality problem — and intentionally illustrative of Stress Test 2's enterprise lesson. The retrieval still works for most questions; severely garbled documents may need a different PDF extraction library.

**Cost seems higher than expected**
Check `utils.py` — the RAG model (Claude Sonnet 4.6 in Tier B) is priced at $15/1M output tokens, which is the most expensive call in the pipeline. Each generation call uses ~600 tokens max, so three calls cost ~$0.027. If costs are significantly higher, you may have accidentally set `max_tokens` much higher than 600 in the generation step.

---

## Research transparency

This lab was built as part of [The AI Navigator](https://ainavigatorhq.substack.com) — a 24-week journey through enterprise AI for business leaders.

The RAG architecture synthesises work from:
- Lewis et al. (2020) — the original RAG paper `arxiv.org/abs/2005.11401`
- LlamaIndex and LangChain documentation
- Pinecone's RAG learning resources
- ChromaDB documentation

All documents used as knowledge bases are publicly available from their original publishers.

---

*Built with OpenRouter · ChromaDB · pdfplumber · python-dotenv*
*Part of the AI Navigator curriculum — [ainavigatorhq.substack.com](https://ainavigatorhq.substack.com)*
