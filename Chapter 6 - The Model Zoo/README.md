⚠️ Experimental prototype exploring prompt architecture patterns.

🎯 Purpose

This project explores a key question in modern AI systems:

Can structured prompt design reduce reliance on expensive models?

It benchmarks a two-stage architecture:

Architect model → designs structured prompt “blueprints”
Worker models → execute those blueprints at lower cost
👤 Who should use this?

This tool is useful for:

AI Engineers / ML Engineers → exploring cost-performance tradeoffs
Product / Platform Engineers → designing scalable LLM pipelines
Prompt Engineers → testing structured prompting strategies
Technical leaders → evaluating model cost optimisation patterns
🤔 Why this matters

In production systems:

Repeated use of high-cost models becomes expensive
Prompt quality is often inconsistent
There is little benchmarking across model tiers

This framework helps you:

Quantify cost vs performance tradeoffs
Experiment with prompt reuse (blueprints)
Evaluate multi-model strategies
🧪 What makes this different?

Instead of comparing models directly, this approach:

Separates thinking (Architect) from execution (Worker)
Treats prompts as reusable assets
Introduces a simple evaluation framework

AI Prompt Calibrator (Prototype)

A lightweight experimental framework to benchmark a two-stage prompt architecture:

Architect model → generates structured prompt “blueprints”
Worker models → execute tasks using those blueprints
💡 Motivation

Most prompt engineering workflows repeatedly rely on high-cost models.

This project explores a simple hypothesis:

If prompts are structured well enough, can cheaper models deliver comparable results?

🏗️ Approach
Convert a natural prompt into a structured “blueprint” using an Architect model
Execute the blueprint across multiple Worker models
Evaluate outputs based on:
Logical completeness (structured prompt adherence)
Correctness (LLM-as-judge)
Cost (token usage)
Latency
📊 What it measures
Logic Score → Presence of structured prompt gates
Correctness Score → Evaluated by a judge model
Cost (USD) → Based on token usage
Latency (seconds)
Final Score → Weighted composite
🚀 How to run
1. Set your API key
export OPENROUTER_API_KEY="your_api_key_here"
2. Install dependencies
pip install -r requirements.txt
3. Run benchmark
python calibrator.py
🧪 Example Prompt

See examples/sample_prompt.txt

🧠 Key Idea

The “blueprint” acts as a reusable abstraction:

Expensive models are used once to design logic
Cheaper models can reuse that logic repeatedly
⚠️ Limitations
Prototype-level implementation
Relies on LLM judge (subjective scoring)
Not optimized for production-scale workloads