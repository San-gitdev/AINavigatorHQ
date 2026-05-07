# Chapter 8 — The Semantic Bouncer
### The AI Navigator | [Substack](https://ainavigatorhq.substack.com) · [LinkedIn](https://www.linkedin.com/in/sandeepdasika/)

> *"A keyword filter blocked 'Project Icarus'. It passed 'the bird that flew too close to the sun'. This lab closes that gap."*

---

## What This Lab Builds

A progressive security pipeline that sits between user input and external LLMs — scrubbing PII, blocking sensitive queries, and ensuring confidential information never reaches external APIs.

Four individual experiments that build progressively, two composite experiments that stress-test everything together. All code generated with Claude and Gemini.

This lab is Chapter 8 of The AI Navigator. It connects directly to [Week 1: The Geometry of Meaning](https://ainavigatorhq.substack.com/p/the-ai-navigator-week-1-the-geometry) — the same vector space we used to map language is now working as a security checkpoint.

---

## Repository Structure

```
Chapter 8 - Semantic Bouncer/
│
├── Individual Experiments/          # Build understanding one layer at a time
│   ├── Lab 1 - Local Llama/         # Local Ollama + small model (the one that fails)
│   │   ├── tools.py
│   │   └── app.py
│   │
│   ├── Lab 2 - Groq Rule Based/     # Groq orchestration + deterministic keyword gate
│   │   └── tools.py
│   │
│   ├── Lab 3 - Groq Presidio/       # Microsoft Presidio for enterprise PII scrubbing
│   │   └── tools.py
│   │
│   └── Lab 4 - Groq Semantic/       # Local embedding bouncer — catches metaphors
│       └── tools.py
│
└── Composite Experiments/           # Full pipelines and benchmarks
    ├── Lab 5 - Enterprise/          # All layers combined, policy-driven
    │   ├── tools.py
    │   └── security_policy.json     # Edit this to customise — no code changes needed
    │
    ├── benchmark.py                 # 60 sentences × 5 setups — accuracy, latency, cost
    └── benchmark2.py                # Extends benchmark with Groq + OpenRouter models
```

---

## The Story in Five Labs

| Lab | Approach | Key Lesson |
|---|---|---|
| 1 | Local Ollama · llama3.2:1b | Small models return CLEAN for everything — unusable for security |
| 2 | Groq + Rule-Based Keywords | Deterministic rules are fast and free for *known* terms |
| 3 | Groq + Microsoft Presidio | Enterprise PII detection covers 50+ entity types |
| 4 | Groq + Embedding Bouncer | Semantic similarity catches metaphors and novel phrasing |
| 5 | Full Enterprise Pipeline | Policy-driven, layered, configurable without code changes |

---

## The Architecture (Lab 5)

```
User Input
    │
    ▼
┌─────────────────────────────────┐
│  Layer 1: PII Scrubber          │  ~5ms    Presidio / regex fallback
│  Strips emails, phones, SSNs    │          Always runs first
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Layer 2: Keyword Gate          │  <1ms    Deterministic, zero cost
│  Blocks known sensitive terms   │          Short-circuits if matched
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Layer 3: Semantic Bouncer      │  ~30ms   Local embeddings only
│  Catches metaphors & novel      │          No data leaves the device
│  phrasing via vector similarity │
└──────────────┬──────────────────┘
               │  CLEAN ✓
               ▼
┌─────────────────────────────────┐
│  External LLM                   │  Only reached if all layers pass
│  (Groq / OpenRouter / any API)  │  Never sees raw PII or sensitive content
└─────────────────────────────────┘
```

**The principle: the LLM is the last door, not the first guard.**

---

## Benchmark Results

60 test sentences across direct references, indirect phrasing, metaphors, PII-containing inputs, and confusable clean inputs.

| Approach | Recall | F1 | Avg Latency | Cost |
|---|---|---|---|---|
| Local small model (1B) | 0% | 0% | 2–30s | $0 |
| Rule-based keywords | ~60%* | — | <1ms | $0 |
| **Embedding bouncer (local)** | **91.4%** | **88.9%** | **14ms** | **$0** |
| Groq Llama 3.3 70B | 0%† | 0% | 54ms | $0 |
| OR Mistral Small 24B | 94.3% | 97.1% | 430ms | ~$0.10/1M |
| OR Gemini 2.0 Flash | 91.4% | 95.5% | 611ms | ~$0.10/1M |
| OR Claude Haiku | 82.9% | 90.6% | 1,232ms | ~$0.80/1M |
| OR Llama 3.3 70B | 94.3% | 95.7% | 530ms | ~$0.20/1M |

*\*Keyword recall depends on list coverage — metaphors and indirect references not caught.*
*†Groq 0% is a prompt formatting issue under investigation, not a model capability failure.*

**Headline finding:** An 80MB model running locally matches paid cloud APIs on accuracy, runs 30x faster, and sends zero data externally.

---

## Prerequisites

### All Labs
```bash
pip install smolagents litellm
```

### Lab 1 — Local Ollama
```bash
pip install ollama
ollama pull llama3.2:1b
```

### Labs 2–5 — Groq (free, no credit card)
```bash
pip install groq litellm
export GROQ_API_KEY=your_key   # Free at console.groq.com
```

### Lab 3 & Lab 5 — Microsoft Presidio
```bash
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_lg
```

### Labs 4, 5 & Benchmarks — Semantic Embeddings
```bash
pip install sentence-transformers
# Downloads ~80MB model on first run, cached afterwards
```

### benchmark2.py — OpenRouter (optional)
```bash
export OPENROUTER_API_KEY=your_key   # At openrouter.ai
```

---

## Running the Labs

### Individual Experiments

```bash
# Lab 1: Watch it fail — everything returns CLEAN
cd "Individual Experiments/Lab 1 - Local Llama"
python app.py

# Lab 2: Keyword gate — fast, reliable for known terms
cd "Individual Experiments/Lab 2 - Groq Rule Based"
python tools.py

# Lab 3: Enterprise PII scrubbing with Presidio
cd "Individual Experiments/Lab 3 - Groq Presidio"
python tools.py

# Lab 4: Semantic bouncer — metaphors now caught
cd "Individual Experiments/Lab 4 - Groq Semantic"
python tools.py
```

### Composite Experiments

```bash
# Lab 5: Full enterprise pipeline with custom policy
cd "Composite Experiments"
python "Lab 5 - Enterprise/tools.py"

# Benchmark: 60 sentences × 5 setups
python benchmark.py --export results

# Benchmark2: Add Groq + OpenRouter model comparison
python benchmark2.py --groq-only --export groq_results
python benchmark2.py --export full_results
```

### Benchmark Output Files
| File | Contents |
|---|---|
| `*_summary.csv` | One row per setup — all metrics |
| `*_report.md` | Publishable markdown table + miss analysis |
| `*_detail.csv` | Per-sentence breakdown across all setups |

---

## Customising the Security Policy (No Code Required)

Edit `Composite Experiments/security_policy.json`:

```json
{
  "keyword_rules": [
    "project icarus",
    "your-new-project-name"
  ],
  "semantic_topics": [
    "Plain English description of a new sensitive topic"
  ],
  "semantic_threshold": 0.4
}
```

**Threshold guide:**
| Value | Behaviour |
|---|---|
| `0.3` | Loose — catches more, higher false positive rate |
| `0.4` | Balanced — recommended starting point |
| `0.6` | Strict — fewer false alarms, may miss edge cases |

No Python knowledge required. Add a line, save the file, run.

---

## How the Semantic Bouncer Works

The embedding bouncer uses vector similarity rather than keyword matching.

1. **At startup** — sensitive topic descriptions are encoded into 384-dimensional vectors and cached (~1 second, runs once)
2. **At runtime** — the input is encoded into a vector (~10ms on CPU)
3. **Comparison** — cosine similarity measures the geometric angle between the input and every sensitive topic vector
4. **Verdict** — if the highest similarity score exceeds the threshold, the input is blocked

This is why *"the bird that flew too close to the sun"* is blocked even without the word "Icarus" — in the semantic space the model learned from training data, Icarus mythology and the codename occupy the same neighbourhood.

The model (`all-MiniLM-L6-v2`) is 80MB, runs entirely on CPU, and processes inputs in ~30ms. No API call. No data leaves the device.

---

## Enterprise Context

This lab is a teaching exercise. The same architecture in productised, enterprise-supported form is available from:

| Vendor | Focus |
|---|---|
| [Nightfall AI](https://nightfall.ai) | ML-powered DLP for cloud environments |
| [Lakera Guard](https://lakera.ai) | Purpose-built LLM security layer |
| [Prompt Security](https://prompt.security) | Enterprise AI firewall with policy management |
| [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/) | Network-layer AI traffic inspection |

Understanding the architecture helps you evaluate these vendors on the right criteria: semantic detection methodology, data sovereignty, latency at scale, and false positive rates.

---

## FAQs

**Why does Lab 1 return CLEAN for everything?**
A 1B parameter model lacks reliable instruction-following for binary classification. It cannot consistently hold a security policy in mind while evaluating inputs. Demonstrated intentionally as the lab's starting failure case.

**Why did Groq models score 0% in benchmark2?**
A prompt formatting issue under investigation — likely token truncation or response parsing with litellm's Groq integration, not a model capability failure. The same models perform well on direct API calls.

**Can I use this in production?**
The pipeline logic is sound. Before deploying you would want to add: audit logging, rate limiting, monitoring and alerting, and proper secrets management for API keys.

**The embedding model downloads on first run — is that expected?**
Yes. `all-MiniLM-L6-v2` (~80MB) downloads from HuggingFace once and is cached locally. Subsequent runs use the cache.

**How do I add sensitive topics without editing code?**
Add a plain English description to `semantic_topics` in `security_policy.json`. No coding required.

---

## Connected Reading

- [Week 1: The Geometry of Meaning](https://ainavigatorhq.substack.com/p/the-ai-navigator-week-1-the-geometry) — the vector space concept this lab makes operational
- [Chapter 8: The Semantic Bouncer](https://ainavigatorhq.substack.com) — full write-up with benchmark analysis and enterprise context
- [The AI Navigator](https://ainavigatorhq.substack.com) — weekly newsletter on enterprise AI adoption

---

*Code generated with Claude and Gemini. Architecture and judgment: human.*
