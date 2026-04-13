import csv
import time
import os
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from api_client import call_openrouter, call_with_heartbeat
from scoring import (
    sanitize_text,
    calculate_logic_score,
    calculate_cost,
    calculate_final_score,
)

ARCHITECT_MODEL = "anthropic/claude-3.5-haiku"
JUDGE_MODEL = "openai/gpt-4o-mini"

WORKER_MODELS = [
    "google/gemini-2.5-flash-lite",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-31b-it",
    "qwen/qwen3.6-plus"
]

RUNS_DIR = "runs"
BLUEPRINT_DIR = "prompt_blueprints"

os.makedirs(RUNS_DIR, exist_ok=True)
os.makedirs(BLUEPRINT_DIR, exist_ok=True)


import hashlib
from datetime import datetime


def get_blueprint_filename(prompt):
    """
    Generates a deterministic filename based on:
    - Current month (YYYY-MM)
    - Hash of the input prompt

    This ensures:
    - Same prompt → same file within a month
    - New month → fresh blueprint (allows evolution)
    """
    month = datetime.now().strftime("%Y-%m")
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:10]

    filename = f"{month}_{prompt_hash}.txt"
    return os.path.join(BLUEPRINT_DIR, filename)


def architect_compile(prompt):
    """
    Generates or reuses a blueprint.

    Logic:
    - If blueprint exists → reuse (cache hit)
    - Else → call Architect model and persist
    """
    filepath = get_blueprint_filename(prompt)

    # ✅ Cache hit → reuse blueprint
    if os.path.exists(filepath):
        print(f"[CACHE HIT] Using existing blueprint: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    print("[CACHE MISS] Generating new blueprint...")

    meta_prompt = f"""
Convert input into structured XML prompt:

<context>, <task_logic>, <constraints>, <output_format>, <thought_process>, <circuit_breaker>

INPUT:
{prompt}
"""
    res = call_openrouter(ARCHITECT_MODEL, meta_prompt)

    if not res:
        return None

    blueprint = res["choices"][0]["message"]["content"]

    # Persist blueprint
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(blueprint)

    print(f"[SAVED] Blueprint stored at: {filepath}")

    return blueprint


def judge_response(blueprint, response):
    """LLM-as-judge scoring"""
    judge_prompt = f"""
Rate RESPONSE vs BLUEPRINT (0-10). Return JSON {{"rating": X}}

BLUEPRINT:
{blueprint}

RESPONSE:
{response}
"""
    res = call_openrouter(JUDGE_MODEL, judge_prompt)

    try:
        import json, re
        content = res["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(match.group()).get("rating", 0)
    except:
        return 0


def evaluate_model(model, blueprint):
    """Run one worker model"""
    response, latency = call_with_heartbeat(model, blueprint)
    if not response:
        return None

    raw = response["choices"][0]["message"]["content"]
    clean = sanitize_text(raw)

    logic = calculate_logic_score(raw)
    correctness = judge_response(blueprint, clean)
    cost = calculate_cost(model, response.get("usage", {}))

    final = calculate_final_score(logic, correctness, cost, latency)

    return [model, logic, correctness, final, cost, latency]

def run_serial(models, blueprint):
    """
    Runs evaluation sequentially (safe for rate limits).
    """
    results = []

    for model in models:
        result = evaluate_model(model, blueprint)
        if result:
            results.append(result)

        # Small delay to avoid throttling
        time.sleep(2)

    return results


def run_parallel(models, blueprint, max_workers):
    """
    Runs evaluation in parallel using ThreadPoolExecutor.
    Use cautiously due to API rate limits.
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(evaluate_model, m, blueprint) for m in models]

        for f in as_completed(futures):
            result = f.result()
            if result:
                results.append(result)

    return results


# ---------------------------
# Main Runner
# ---------------------------
def run(prompt, parallelism=1):
    """
    Main orchestration:
    1. Generate blueprint
    2. Run worker evaluations (serial or parallel)
    3. Store results with timestamp
    """
    print("\n🚀 Starting benchmark...\n")

    blueprint = architect_compile(prompt)
    if not blueprint:
        print("❌ Blueprint generation failed")
        return

    # Choose execution mode
    if parallelism <= 1:
        print("Running in SERIAL mode")
        results = run_serial(WORKER_MODELS, blueprint)
    else:
        print(f"Running in PARALLEL mode (workers={parallelism})")
        results = run_parallel(WORKER_MODELS, blueprint, parallelism)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(RUNS_DIR, f"run_{timestamp}.csv")

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["Model", "Logic", "Correctness", "Final Score", "Cost", "Latency"]
        )
        writer.writerows(results)

    print(f"\n✅ Run complete: {output_file}")


# ---------------------------
# CLI Entry
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Prompt Calibrator")
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel worker requests (default: 1)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Analyze the current geopolitical situation in the Middle East and predict potential flashpoints for conflict in the next 6 months.",
        help="Prompt to evaluate",
    )

    args = parser.parse_args()

    run(args.prompt, parallelism=args.parallel)