# utils.py — W9 RAG Lab
# Model registry sourced directly from OpenRouter API (May 2026)
# Pricing in USD per token

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Model Registry ─────────────────────────────────────────────────────────────
# All IDs verified against https://openrouter.ai/api/v1/models (May 13, 2026)
# input_cost / output_cost = USD per token

MODEL_REGISTRY = {
    "baseline": {
        "name":         "Mistral Small 4",
        "id":           "mistralai/mistral-small-2603",
        "input_cost":   0.00000015,   # $0.15 / 1M tokens
        "output_cost":  0.00000060,   # $0.60 / 1M tokens
        "purpose":      "Act 1 — amnesiac baseline (no RAG context)",
        "notes":        "Capable enough to hallucinate confidently on specific facts"
    },
    "rag": {
        "name":         "Claude Sonnet 4.6",
        "id":           "anthropic/claude-sonnet-4.6",
        "input_cost":   0.000003,     # $3.00 / 1M tokens
        "output_cost":  0.000015,     # $15.00 / 1M tokens
        "purpose":      "Act 2 & 3 — grounded RAG generation with citations",
        "notes":        "Strong instruction following and source attribution"
    },
    "rag_budget": {
        "name":         "Mistral Small 4",
        "id":           "mistralai/mistral-small-2603",
        "input_cost":   0.00000015,
        "output_cost":  0.00000060,
        "purpose":      "Act 2 budget alternative — same model as baseline for cost comparison",
        "notes":        "Use to isolate RAG vs no-RAG effect independent of model quality"
    },
    "fast": {
        "name":         "GPT-5.4 Nano",
        "id":           "openai/gpt-5.4-nano",
        "input_cost":   0.0000002,    # $0.20 / 1M tokens
        "output_cost":  0.00000125,   # $1.25 / 1M tokens
        "purpose":      "Stress tests — fast iteration across all three failure modes",
        "notes":        "Low latency good for repeated stress test runs"
    }
}

# ── Cost Tracker ───────────────────────────────────────────────────────────────

class CostTracker:
    def __init__(self):
        self.sessions = []

    def log(self, model_key: str, prompt_tokens: int, completion_tokens: int, label: str = ""):
        model = MODEL_REGISTRY[model_key]
        input_cost  = prompt_tokens * model["input_cost"]
        output_cost = completion_tokens * model["output_cost"]
        total_cost  = input_cost + output_cost

        entry = {
            "label":             label or model_key,
            "model_name":        model["name"],
            "prompt_tokens":     prompt_tokens,
            "completion_tokens": completion_tokens,
            "input_cost":        input_cost,
            "output_cost":       output_cost,
            "total_cost":        total_cost
        }
        self.sessions.append(entry)
        return entry

    def print_summary(self):
        print("\n" + "=" * 65)
        print("COST SUMMARY")
        print("=" * 65)
        print(f"{'Label':<25} {'Model':<22} {'Tokens':>8} {'Cost (USD)':>12}")
        print("-" * 65)

        grand_total = 0
        for s in self.sessions:
            tokens = s["prompt_tokens"] + s["completion_tokens"]
            print(f"{s['label']:<25} {s['model_name']:<22} {tokens:>8} ${s['total_cost']:>11.6f}")
            grand_total += s["total_cost"]

        print("-" * 65)
        print(f"{'TOTAL':<48} ${grand_total:>11.6f}")
        print("=" * 65)

# ── Client Factory ─────────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    """Single OpenRouter client — all models route through here."""
    return OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://ainavigatorhq.substack.com",
            "X-Title":      "AI Navigator RAG Lab W9",
        }
    )

def call_model(
    client: OpenAI,
    model_key: str,
    messages: list,
    tracker: CostTracker,
    label: str = "",
    temperature: float = 0.7,
    max_tokens: int = 512
) -> str:
    """
    Unified model call. Always logs cost.
    Returns the response text.
    """
    model_id = MODEL_REGISTRY[model_key]["id"]

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )

    usage = response.usage
    tracker.log(
        model_key=model_key,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        label=label or model_key
    )

    return response.choices[0].message.content

# ── Shared Test Questions ──────────────────────────────────────────────────────
# Calibrated for BoE MPR February 2025
# Specific enough to require document knowledge — can't be guessed

QUESTIONS = [
    {
        "id": "Q1",
        "text": "What exact percentage did the Bank of England forecast for UK GDP growth in 2025 in the February 2025 Monetary Policy Report?",
        "topic": "GDP forecast"
    },
    {
        "id": "Q2",
        "text": "What was the MPC's precise CPI inflation forecast for Q4 2025 published in the February 2025 report?",
        "topic": "Inflation forecast"
    },
    {
        "id": "Q3",
        "text": "Which specific external risk factor did the Bank of England's February 2025 report identify as the primary threat to the UK economic outlook?",
        "topic": "External risk factors"
    }
]

# ── Print Model Registry ───────────────────────────────────────────────────────

def print_model_registry():
    print("\n" + "=" * 65)
    print("MODEL REGISTRY")
    print("=" * 65)
    for key, m in MODEL_REGISTRY.items():
        print(f"\n[{key.upper()}]")
        print(f"  Name:    {m['name']}")
        print(f"  ID:      {m['id']}")
        print(f"  Input:   ${m['input_cost'] * 1_000_000:.2f} / 1M tokens")
        print(f"  Output:  ${m['output_cost'] * 1_000_000:.2f} / 1M tokens")
        print(f"  Purpose: {m['purpose']}")
    print("=" * 65)