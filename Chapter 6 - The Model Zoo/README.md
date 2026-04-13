> ⚠️ Experimental prototype exploring prompt architecture patterns.

## 🎯 Purpose

This project explores a key question in modern AI systems:

> **Can structured prompt design reduce reliance on expensive models?**

It benchmarks a two-stage architecture:

- **Architect model** → designs structured prompt "blueprints"
- **Worker models** → execute those blueprints at lower cost

---

## 👤 Who should use this?

This tool is useful for:

- **AI Engineers / ML Engineers** → exploring cost-performance tradeoffs
- **Product / Platform Engineers** → designing scalable LLM pipelines
- **Prompt Engineers** → testing structured prompting strategies
- **Technical leaders** → evaluating model cost optimisation patterns

---

## 🤔 Why this matters

In production systems:

- Repeated use of high-cost models becomes expensive
- Prompt quality is often inconsistent
- There is little benchmarking across model tiers

This framework helps you:

- Quantify cost vs performance tradeoffs
- Experiment with prompt reuse (blueprints)
- Evaluate multi-model strategies

---

## 🧪 What makes this different?

Instead of comparing models directly, this approach:

- Separates **thinking** (Architect) from **execution** (Worker)
- Treats prompts as **reusable assets**
- Introduces a simple **evaluation framework**

---

## AI Prompt Calibrator (Prototype)

A lightweight experimental framework to benchmark a two-stage prompt architecture:

- **Architect model** → generates structured prompt "blueprints"
- **Worker models** → execute tasks using those blueprints

### 💡 Motivation

Most prompt engineering workflows repeatedly rely on high-cost models.

This project explores a simple hypothesis:

> If prompts are structured well enough, can cheaper models deliver comparable results?

---

## 🏗️ Approach

1. Convert a natural prompt into a structured "blueprint" using an Architect model
2. Execute the blueprint across multiple Worker models
3. Evaluate outputs based on:
   - Logical completeness (structured prompt adherence)
   - Correctness (LLM-as-judge)
   - Cost (token usage)
   - Latency

---

## 📊 What it measures

| Metric | Description |
|---|---|
| **Logic Score** | Presence of structured prompt gates |
| **Correctness Score** | Evaluated by a judge model |
| **Cost (USD)** | Based on token usage |
| **Latency (seconds)** | End-to-end response time |
| **Final Score** | Weighted composite (see below) |

### Final Score formula

The Final Score is a composite metric balancing three dimensions:

| Dimension | Weight | What it measures |
|---|---|---|
| Task accuracy | 60% | Correctness against ground-truth or rubric |
| Latency | 20% | Inverse of p50 response time — faster = higher |
| Cost efficiency | 20% | Inverse of cost per call — cheaper = higher |

```
Final Score = 0.6 × accuracy + 0.2 × norm(1/latency) + 0.2 × norm(1/cost)
```

Latency and cost are min-max normalised across all models in a run, so scores are comparable within a run. Interpret cross-run comparisons with care when the model set differs. A score above **0.85** is considered strong for general-purpose tasks.

---

## 🚀 How to run

### 1. Set your API key
```bash
export OPENROUTER_API_KEY="your_api_key_here"
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run benchmark
```bash
python calibrator.py
```

Each run produces a CSV in the `runs/` folder, stamped with a `Run_YYYYMMDD_HHMMSS` identifier so results are never overwritten.

---

## 🧪 Example Prompt

See `examples/sample_prompt.txt`

---

## 📈 Scoring Dashboard

After one or more benchmark runs, you can explore results visually using the included Streamlit dashboard.

### Launch the dashboard
```bash
streamlit run streamlit_dashboard.py
```

This opens an interactive app at `http://localhost:8501`.

### What the dashboard shows

**Summary cards** — top scorer, lowest cost model, fastest model, and total rows loaded, updated live as you apply filters.

**Score vs cost** — scatter plot of Final Score against cost per call, colour-coded by run. A Pareto frontier line highlights the non-dominated models — those where no alternative is simultaneously cheaper and higher-scoring.

**Score vs latency** — the same scatter view with latency on the x-axis, useful for identifying models that score well but introduce unacceptable response times.

**Score ranking** — horizontal bar chart ranking every model by its average Final Score across all selected runs. Bars are colour-intensity encoded so relative performance is readable at a glance without needing to read exact axis values.

**Heatmap** — compares every model across all three key dimensions (score, cost, latency) in a single view. All three metrics are min-max normalised to a shared 0–1 scale, with cost and latency inverted so that darker always means better. Raw averages are shown as cell labels so you retain the actual numbers.

**Raw data table** — sortable, filterable view of every row, with a one-click CSV export of whatever subset is currently in view.

### Sidebar filters

| Filter | Effect |
|---|---|
| **Runs** | Show/hide individual benchmark runs |
| **Models** | Isolate specific models |
| **Score range** | Narrow to a score band of interest |

### Loading data

The dashboard reads all CSVs from the `runs/` folder automatically. You can also drag and drop CSVs directly into the file uploader in the sidebar — useful for comparing runs from different machines or teammates.

### CSV format

Each CSV must have these columns:

```
Model, Final Score, Cost, Latency
```

The `Run` column is added automatically by `scoring.py` using the file's last-modified timestamp.

---

## 🧠 Key Idea

The "blueprint" acts as a reusable abstraction:

- Expensive models are used **once** to design logic
- Cheaper models can **reuse** that logic repeatedly

---

## ⚠️ Limitations

- Prototype-level implementation
- Relies on LLM judge (subjective scoring)
- Not optimized for production-scale workloads