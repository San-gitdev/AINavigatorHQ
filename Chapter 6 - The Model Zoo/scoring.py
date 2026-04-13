import re

COST_TABLE = {
    'anthropic/claude-3.5-haiku': 0.25,
    'google/gemini-2.0-flash-lite:preview': 0.10,
    'nvidia/nemotron-3-super-120b-a12b:free': 0.00,
    'meta-llama/llama-3.3-70b-instruct:free': 0.00,
    'qwen/qwen3.6-plus:free': 0.00,
    'nvidia/nemotron-3-nano-30b-a3b:free': 0.00,
    'openai/gpt-4o-mini': 0.15,
    "google/gemma-4-31b-it:free": 0.00,
    "google/gemma-4-31b-it": 0.14,
    "qwen/qwen3.6-plus": 0.00
}


def sanitize_text(text):
    text = re.sub(r"[┌─┐└─┘│┤├┼┴┬║═╔╗╚╝╠╣╦╩╬]", "", text)
    text = re.sub(r"\*\*", "", text)
    return text.strip()


def calculate_logic_score(text):
    gates = [
        "<context>",
        "<task_logic>",
        "<constraints>",
        "<output_format>",
        "<thought_process>",
        "<circuit_breaker>",
    ]
    text_lower = text.lower()
    return sum(1 for gate in gates if gate in text_lower)


def calculate_cost(model_id, usage):
    if not usage:
        return 0.0
    total_tokens = usage.get("total_tokens", 0)
    rate = COST_TABLE.get(model_id, 0.15)
    return (total_tokens / 1_000_000) * rate


def calculate_final_score(logic_score, correctness, cost, latency):
    logic_component = (logic_score / 6.0) * 100
    correctness_component = correctness * 10

    cost_penalty = max(0, (cost - 0.01) * 1000)
    latency_penalty = max(0, (latency - 60) * 0.5)

    final = (logic_component * 0.4) + (correctness_component * 0.4)
    final -= cost_penalty + latency_penalty

    return round(max(0, min(100, final)), 1)