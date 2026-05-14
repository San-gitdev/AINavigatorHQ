# utils.py — W9 RAG Lab
# Model registry sourced directly from OpenRouter API (May 2026)
#
# TWO TIERS:
#   TIER A — Free models (no credits required, rate limited)
#   TIER B — Paid models (costs <$1 per full lab run, better quality)
#
# Set TIER = "A" or "B" at the top of this file,
# or pass --tier A / --tier B when running any script.

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Tier Selection ─────────────────────────────────────────────────────────────
# Change this to "A" for free models, "B" for paid models.
# Scripts also accept --tier A or --tier B as a CLI argument.

DEFAULT_TIER = "B"

# ── Model Registry ─────────────────────────────────────────────────────────────
# All IDs verified against https://openrouter.ai/api/v1/models (May 2026)
# input_cost / output_cost = USD per token
# Free models use :free suffix — rate limited but no credit cost

MODEL_TIERS = {

    "A": {
        "_label": "FREE TIER (no credits required — may be slower)",
        "baseline": {
            "name":        "Gemma 4 26B A4B (free)",
            "id":          "google/gemma-4-26b-a4b-it:free",
            "input_cost":  0.0,
            "output_cost": 0.0,
            "purpose":     "Act 1 — amnesiac baseline (no RAG context)",
            "notes":       "Free, capable enough to hallucinate on specific facts"
        },
        "rag": {
            "name":        "NVIDIA Nemotron 3 Super (free)",
            "id":          "nvidia/nemotron-3-super-120b-a12b:free",
            "input_cost":  0.0,
            "output_cost": 0.0,
            "purpose":     "Act 2 & 3 — grounded RAG generation with citations",
            "notes":       "Free 120B model, strong instruction following"
        },
        "fast": {
            "name":        "Gemma 4 31B (free)",
            "id":          "google/gemma-4-31b-it:free",
            "input_cost":  0.0,
            "output_cost": 0.0,
            "purpose":     "Stress tests — free iteration across failure modes",
            "notes":       "Free, good reasoning capabilities"
        },
        "embedding": {
            "name":        "text-embedding-3-small (free tier)",
            "id":          "openai/text-embedding-3-small",
            "input_cost":  0.0,
            "output_cost": 0.0,
            "purpose":     "Act 2 — chunk and query embedding via OpenRouter",
            "notes":       "OpenRouter free allowance covers typical lab usage"
        }
    },

    "B": {
        "_label": "PAID TIER (<$1 per full lab run — faster, higher quality)",
        "baseline": {
            "name":        "Mistral Small 4",
            "id":          "mistralai/mistral-small-2603",
            "input_cost":  0.00000015,   # $0.15 / 1M tokens
            "output_cost": 0.00000060,   # $0.60 / 1M tokens
            "purpose":     "Act 1 — amnesiac baseline (no RAG context)",
            "notes":       "Cheap, fast, confident hallucinator"
        },
        "rag": {
            "name":        "Claude Sonnet 4.6",
            "id":          "anthropic/claude-sonnet-4.6",
            "input_cost":  0.000003,     # $3.00 / 1M tokens
            "output_cost": 0.000015,     # $15.00 / 1M tokens
            "purpose":     "Act 2 & 3 — grounded RAG generation with citations",
            "notes":       "Best citation quality and instruction following"
        },
        "fast": {
            "name":        "GPT-5.4 Nano",
            "id":          "openai/gpt-5.4-nano",
            "input_cost":  0.0000002,    # $0.20 / 1M tokens
            "output_cost": 0.00000125,   # $1.25 / 1M tokens
            "purpose":     "Stress tests — fast iteration",
            "notes":       "Low latency for repeated stress test runs"
        },
        "embedding": {
            "name":        "text-embedding-3-small",
            "id":          "openai/text-embedding-3-small",
            "input_cost":  0.00000002,   # $0.02 / 1M tokens
            "output_cost": 0.0,
            "purpose":     "Act 2 — chunk and query embedding via OpenRouter",
            "notes":       "Same model both tiers; Tier B tracks cost, Tier A treats as free"
        }
    }

}

# ── Active Registry (set by tier selection) ────────────────────────────────────

def get_model_registry(tier: str = DEFAULT_TIER) -> dict:
    tier = tier.upper()
    if tier not in MODEL_TIERS:
        raise ValueError(f"Invalid tier '{tier}'. Choose 'A' (free) or 'B' (paid).")
    registry = {k: v for k, v in MODEL_TIERS[tier].items() if not k.startswith("_")}
    return registry

# Keep a mutable reference so call_model() can read the active registry
_active_registry = get_model_registry(DEFAULT_TIER)
_active_tier     = DEFAULT_TIER


def set_tier(tier: str):
    """Call this at script startup after parsing --tier argument."""
    global _active_registry, _active_tier
    _active_tier     = tier.upper()
    _active_registry = get_model_registry(_active_tier)
    print(f"\nTier selected: {_active_tier} — {MODEL_TIERS[_active_tier]['_label']}")


# ── Cost Tracker ───────────────────────────────────────────────────────────────

class CostTracker:
    def __init__(self):
        self.sessions = []

    def log(self, model_key: str, prompt_tokens: int,
            completion_tokens: int, label: str = ""):
        model       = _active_registry[model_key]
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
        tier_label = MODEL_TIERS[_active_tier]["_label"]
        print("\n" + "=" * 65)
        print(f"COST SUMMARY — Tier {_active_tier}: {tier_label}")
        print("=" * 65)
        print(f"{'Label':<25} {'Model':<22} {'Tokens':>8} {'Cost (USD)':>12}")
        print("-" * 65)

        grand_total = 0
        for s in self.sessions:
            tokens = s["prompt_tokens"] + s["completion_tokens"]
            cost_str = "FREE" if s["total_cost"] == 0 else f"${s['total_cost']:>10.6f}"
            print(f"{s['label']:<25} {s['model_name']:<22} {tokens:>8} {cost_str:>12}")
            grand_total += s["total_cost"]

        print("-" * 65)
        total_str = "FREE" if grand_total == 0 else f"${grand_total:>10.6f}"
        print(f"{'TOTAL':<48} {total_str:>12}")
        print("=" * 65)


# ── Client Factory ─────────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    """Single OpenRouter client — all models route through here."""
    return OpenAI(
        api_key  = os.getenv("OPENROUTER_API_KEY"),
        base_url = "https://openrouter.ai/api/v1",
        default_headers = {
            "HTTP-Referer": "https://ainavigatorhq.substack.com",
            "X-Title":      "AI Navigator RAG Lab W9",
        }
    )


def call_model(
    client:      OpenAI,
    model_key:   str,
    messages:    list,
    tracker:     CostTracker,
    label:       str   = "",
    temperature: float = 0.7,
    max_tokens:  int   = 512
) -> str:
    """
    Unified model call. Always logs cost (or $0.00 for free tier).
    Returns the response text.
    """
    model_id = _active_registry[model_key]["id"]

    response = client.chat.completions.create(
        model       = model_id,
        messages    = messages,
        temperature = temperature,
        max_tokens  = max_tokens
    )

    usage = response.usage
    tracker.log(
        model_key         = model_key,
        prompt_tokens     = usage.prompt_tokens,
        completion_tokens = usage.completion_tokens,
        label             = label or model_key
    )

    return response.choices[0].message.content


# ── Display Helpers ────────────────────────────────────────────────────────────

def print_model_registry():
    registry   = _active_registry
    tier_label = MODEL_TIERS[_active_tier]["_label"]

    print("\n" + "=" * 65)
    print(f"MODEL REGISTRY — Tier {_active_tier}: {tier_label}")
    print("=" * 65)
    for key, m in registry.items():
        cost_str = (
            "FREE"
            if m["input_cost"] == 0
            else f"${m['input_cost']*1_000_000:.2f} in / ${m['output_cost']*1_000_000:.2f} out per 1M tokens"
        )
        print(f"\n[{key.upper()}]")
        print(f"  Name:    {m['name']}")
        print(f"  ID:      {m['id']}")
        print(f"  Cost:    {cost_str}")
        print(f"  Purpose: {m['purpose']}")
    print("=" * 65)


def add_tier_argument(parser):
    """
    Call this in every script's argparse setup.
    Adds --tier A / --tier B flag consistently.
    """
    parser.add_argument(
        "--tier",
        type    = str,
        default = DEFAULT_TIER,
        choices = ["A", "B", "a", "b"],
        help    = (
            "Model tier: "
            "A = free models (no credits, slower) | "
            "B = paid models (<$1 per run, faster) "
            f"[default: {DEFAULT_TIER}]"
        )
    )