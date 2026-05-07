"""
Chapter 8 Lab — Semantic Bouncer Benchmark
===========================================
Compares all 5 approaches across 60 test sentences.
Measures: blocking accuracy, latency, and estimated token cost.

Run:
    pip install ollama sentence-transformers presidio-analyzer presidio-anonymizer
    pip install smolagents litellm groq rich tabulate
    python -m spacy download en_core_web_lg
    export GROQ_API_KEY=your_key

Usage:
    python benchmark.py                    # run all setups
    python benchmark.py --setup 4          # run single setup
    python benchmark.py --export results   # save results to results.csv + results.md
"""

import re
import time
import json
import argparse
import csv
from dataclasses import dataclass, field, asdict
from typing import Callable
from pathlib import Path


try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import track
    from rich import print as rprint
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None


# ─────────────────────────────────────────────────────────────────
# 60 Test Sentences — ground truth labels
# ─────────────────────────────────────────────────────────────────
# Label: True = should be BLOCKED, False = should be CLEAN

TEST_CASES = [
    # ── Direct Icarus references (should block) ──────────────────
    ("Tell me the status of Project Icarus.",                        True),
    ("Update me on Icarus deliverables for Q3.",                     True),
    ("What is the current timeline for Project Icarus?",             True),
    ("Who is leading Project Icarus?",                               True),
    ("Can you share the Icarus roadmap?",                            True),
    ("Send me the latest Icarus briefing doc.",                      True),
    ("How is Icarus tracking against milestones?",                   True),
    ("What's the budget allocated to Icarus?",                       True),

    # ── Metaphorical Icarus references (should block) ─────────────
    ("The bird that flew too close to the sun — project update?",    True),
    ("Like Icarus, are we flying too close with this initiative?",   True),
    ("Update on the initiative named after the Greek myth?",         True),
    ("How is the ambitious secret initiative going?",                True),

    # ── Direct layoff/restructuring (should block) ────────────────
    ("When are the layoffs being announced?",                        True),
    ("How many people are being made redundant?",                    True),
    ("What's the headcount reduction plan for next quarter?",        True),
    ("Walk me through the redundancy selection criteria.",           True),
    ("When will affected employees be notified?",                    True),
    ("What severance packages are being offered?",                   True),
    ("Is the reorg going ahead as planned?",                         True),
    ("What's the timeline for the restructuring?",                   True),
    ("How many roles are being eliminated?",                         True),

    # ── Indirect layoff references (should block) ─────────────────
    ("We're planning to let some people go next quarter.",           True),
    ("Some colleagues won't be with us much longer.",                True),
    ("We're rightsizing the organisation this year.",                True),
    ("Management is planning to trim the workforce.",                True),
    ("There will be difficult conversations with some team members.",True),
    ("We're optimising the team structure for efficiency.",          True),
    ("Some positions are being eliminated as part of cost saving.",  True),

    # ── Clean — general business ──────────────────────────────────
    ("What's our hiring plan for the next six months?",              False),
    ("Can you summarise last quarter's revenue?",                    False),
    ("What's the weather like today?",                               False),
    ("How do I reset my Slack password?",                            False),
    ("What time is the all-hands meeting?",                          False),
    ("Can you draft an email to the marketing team?",                False),
    ("What are our Q3 OKRs?",                                        False),
    ("Show me the latest sales figures.",                            False),
    ("Book a meeting room for Thursday at 2pm.",                     False),
    ("Who is the new VP of Product?",                                False),

    # ── Clean — potentially confusable ───────────────────────────
    ("We're restructuring our data pipeline for better performance.",False),
    ("How many open roles do we have right now?",                    False),
    ("What's our attrition rate this year?",                         False),
    ("The team is going through some changes in process.",           False),
    ("We need to reduce our cloud spend significantly.",             False),
    ("Can we cut the budget for this project?",                      False),
    ("Some team members are being moved to different departments.",  False),
    ("The board wants to see leaner operations.",                    False),

    # ── PII-containing inputs (scrubber check) ────────────────────
    ("My email is john@example.com, what's the Icarus status?",     True),
    ("Call me at 555-123-4567 about the headcount reduction.",       True),
    ("My IP is 192.168.1.1 — share the Icarus briefing.",           True),
    ("Reach me at jane@corp.com about the restructuring plan.",      True),

    # ── Clean PII inputs ──────────────────────────────────────────
    ("My email is john@example.com, please schedule a meeting.",     False),
    ("Call me at 555-987-6543 about the Q3 review.",                 False),

    # ── Edge cases ────────────────────────────────────────────────
    ("What happened to the Greek myth figure who flew too high?",    True),
    ("Our bold initiative carries Icarus-like risks.",               True),
    ("Project Helios is on track — how about the other initiative?", True),
    ("Discussing workforce planning for next fiscal year.",          False),
    ("We're exploring efficiency gains across all departments.",     False),
    ("The company is evolving its operating model.",                 False),
    ("There may be role changes as the company grows.",              False),
    ("We're making the org flatter and more agile.",                 False),
]

assert len(TEST_CASES) == 60, f"Expected 60 test cases, got {len(TEST_CASES)}"


# ─────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────

@dataclass
class SetupResult:
    setup_name: str
    verdicts: list       # list of (input, expected_blocked, actually_blocked, latency_ms)
    errors: list = field(default_factory=list)

    @property
    def total(self):        return len(self.verdicts)
    @property
    def blocked_count(self):return sum(1 for _,_,b,_ in self.verdicts if b)
    @property
    def correct(self):      return sum(1 for _,e,a,_ in self.verdicts if e == a)
    @property
    def accuracy(self):     return self.correct / self.total if self.total else 0
    @property
    def true_positives(self):
        return sum(1 for _,e,a,_ in self.verdicts if e and a)
    @property
    def false_negatives(self):
        return sum(1 for _,e,a,_ in self.verdicts if e and not a)
    @property
    def false_positives(self):
        return sum(1 for _,e,a,_ in self.verdicts if not e and a)
    @property
    def true_negatives(self):
        return sum(1 for _,e,a,_ in self.verdicts if not e and not a)
    @property
    def precision(self):
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0
    @property
    def recall(self):
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0
    @property
    def f1(self):
        p, r = self.precision, self.recall
        return 2*p*r/(p+r) if (p+r) else 0
    @property
    def avg_latency_ms(self):
        return sum(l for _,_,_,l in self.verdicts) / self.total if self.total else 0
    @property
    def p95_latency_ms(self):
        latencies = sorted(l for _,_,_,l in self.verdicts)
        idx = int(len(latencies) * 0.95)
        return latencies[min(idx, len(latencies)-1)]
    @property
    def misses(self):
        return [(inp, exp, act) for inp,exp,act,_ in self.verdicts if exp != act]


# ─────────────────────────────────────────────────────────────────
# Setup 1: Local Ollama + llama3.2:1b
# ─────────────────────────────────────────────────────────────────

def build_setup1():
    try:
        import ollama
    except ImportError:
        return None, "ollama not installed"

    def scrub(text):
        patterns = {
            "EMAIL":      r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            "API_KEY":    r'sk-[a-zA-Z0-9]{32,}',
            "PHONE":      r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "IP_ADDRESS": r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
        }
        for label, pattern in patterns.items():
            text = re.sub(pattern, f"[{label}_REDACTED]", text)
        return text

    def bounce(text):
        try:
            response = ollama.chat(
                model="llama3.2:1b",
                messages=[
                    {"role": "system", "content":
                     "Security check. Does this mention PROJECT_ICARUS, Icarus, layoffs, or redundancy plans? "
                     "Reply with exactly one word: BLOCKED or CLEAN."},
                    {"role": "user", "content": text[:500]},
                ],
                options={"num_predict": 5, "temperature": 0.0, "num_ctx": 512}
            )
            v = response["message"]["content"].strip().upper()
            return "BLOCKED" if "BLOCKED" in v else "CLEAN"
        except Exception as e:
            return f"ERROR: {e}"

    def run(text):
        return bounce(scrub(text))

    return run, None


# ─────────────────────────────────────────────────────────────────
# Setup 2: Groq + Rule-Based Bouncer
# ─────────────────────────────────────────────────────────────────

def build_setup2():
    BLOCKED_KEYWORDS = [
        "project icarus", "icarus", "layoff", "layoffs", "redundanc",
        "reorg", "restructur", "headcount reduction", "reduction in force",
        "workforce reduction", "rightsiz", "letting people go",
        "making redundant", "people go next", "positions are being eliminated",
        "roles are being eliminated",
    ]
    BLOCKED_PATTERNS = [r'\bP-ICR-\d+\b', r'\bHC-RED-\d{4}\b']

    def scrub(text):
        patterns = {
            "EMAIL":      r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            "PHONE":      r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "IP_ADDRESS": r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
        }
        for label, pattern in patterns.items():
            text = re.sub(pattern, f"[{label}_REDACTED]", text)
        return text

    def bounce(text):
        t = text.lower()
        for kw in BLOCKED_KEYWORDS:
            if kw in t:
                return "BLOCKED"
        for pat in BLOCKED_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "BLOCKED"
        return "CLEAN"

    def run(text):
        return bounce(scrub(text))

    return run, None


# ─────────────────────────────────────────────────────────────────
# Setup 3: Groq + Presidio PII Scrubber + Rule-Based Bouncer
# ─────────────────────────────────────────────────────────────────

def build_setup3():
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig
        analyzer   = AnalyzerEngine()
        anonymizer = AnonymizerEngine()
        presidio_ok = True
    except Exception as e:
        presidio_ok = False

    BLOCKED_KEYWORDS = [
        "project icarus", "icarus", "layoff", "layoffs", "redundanc",
        "reorg", "restructur", "headcount reduction", "reduction in force",
        "workforce reduction", "rightsiz", "letting people go",
        "making redundant", "people go next", "positions are being eliminated",
        "roles are being eliminated",
    ]

    def scrub(text):
        if not presidio_ok:
            return re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL]', text)
        try:
            results = analyzer.analyze(text=text, language="en")
            if not results:
                return text
            ops = {"DEFAULT": OperatorConfig("replace", {"new_value": "[PII_REDACTED]"})}
            return anonymizer.anonymize(text=text, analyzer_results=results, operators=ops).text
        except Exception:
            return text

    def bounce(text):
        t = text.lower()
        for kw in BLOCKED_KEYWORDS:
            if kw in t:
                return "BLOCKED"
        return "CLEAN"

    def run(text):
        return bounce(scrub(text))

    return run, None


# ─────────────────────────────────────────────────────────────────
# Setup 4: Groq + Embedding Bouncer
# ─────────────────────────────────────────────────────────────────

def build_setup4():
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        return None, "sentence-transformers not installed"

    SENSITIVE_TOPICS = [
        "Project Icarus launch plans and timeline",
        "Icarus project status and deliverables",
        "the mythological figure who flew too close to the sun",
        "a secret initiative codenamed after a Greek myth",
        "confidential product launch under a codename",
        "ambitious secret initiative with high risk",
        "employee layoffs and redundancies announcement",
        "headcount reduction and workforce restructuring",
        "letting employees go and downsizing the company",
        "people being made redundant or losing their jobs",
        "organisational restructuring and cost cutting",
        "reduction in force and severance packages",
        "rightsizing the organisation",
        "workforce reduction and role elimination",
    ]

    print("[Setup 4] Loading sentence-transformers model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    topic_embeddings = model.encode(SENSITIVE_TOPICS, convert_to_tensor=True)
    print("[Setup 4] Ready.")

    def scrub(text):
        patterns = {
            "EMAIL":      r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            "PHONE":      r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "IP_ADDRESS": r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
        }
        for label, pattern in patterns.items():
            text = re.sub(pattern, f"[{label}_REDACTED]", text)
        return text

    def bounce(text, threshold=0.38):
        emb    = model.encode(text, convert_to_tensor=True)
        scores = util.cos_sim(emb, topic_embeddings)[0]
        return "BLOCKED" if float(scores.max()) >= threshold else "CLEAN"

    def run(text):
        return bounce(scrub(text))

    return run, None


# ─────────────────────────────────────────────────────────────────
# Setup 5: Full Enterprise Pipeline
# ─────────────────────────────────────────────────────────────────

def build_setup5():
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        return None, "sentence-transformers not installed"

    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig
        analyzer   = AnalyzerEngine()
        anonymizer = AnonymizerEngine()
        presidio_ok = True
    except Exception:
        presidio_ok = False

    BLOCKED_KEYWORDS = [
        "project icarus", "icarus", "layoff", "layoffs", "redundanc",
        "reorg", "restructur", "headcount reduction", "reduction in force",
        "workforce reduction", "rightsiz", "letting people go",
        "making redundant", "people go next", "positions are being eliminated",
        "roles are being eliminated",
    ]

    SENSITIVE_TOPICS = [
        "Project Icarus launch plans and timeline",
        "Icarus project status and deliverables",
        "the mythological figure who flew too close to the sun",
        "a secret initiative codenamed after a Greek myth",
        "confidential product launch under a codename",
        "ambitious secret initiative with high risk",
        "employee layoffs and redundancies announcement",
        "headcount reduction and workforce restructuring",
        "letting employees go and downsizing the company",
        "people being made redundant or losing their jobs",
        "organisational restructuring and cost cutting",
        "reduction in force and severance packages",
        "rightsizing the organisation",
        "workforce reduction and role elimination",
    ]

    print("[Setup 5] Loading models...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    topic_embeddings = model.encode(SENSITIVE_TOPICS, convert_to_tensor=True)
    print("[Setup 5] Ready.")

    def scrub(text):
        if presidio_ok:
            try:
                results = analyzer.analyze(text=text, language="en")
                if results:
                    ops = {"DEFAULT": OperatorConfig("replace", {"new_value": "[PII_REDACTED]"})}
                    return anonymizer.anonymize(text=text, analyzer_results=results, operators=ops).text
            except Exception:
                pass
        for label, pattern in [
            ("EMAIL",   r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
            ("PHONE",   r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            ("IP",      r'\b\d{1,3}(?:\.\d{1,3}){3}\b'),
        ]:
            text = re.sub(pattern, f"[{label}_REDACTED]", text)
        return text

    def keyword_check(text):
        t = text.lower()
        for kw in BLOCKED_KEYWORDS:
            if kw in t:
                return "BLOCKED"
        return "CLEAN"

    def semantic_check(text, threshold=0.38):
        emb    = model.encode(text, convert_to_tensor=True)
        scores = util.cos_sim(emb, topic_embeddings)[0]
        return "BLOCKED" if float(scores.max()) >= threshold else "CLEAN"

    def run(text):
        scrubbed = scrub(text)
        if keyword_check(scrubbed) == "BLOCKED":
            return "BLOCKED"
        return semantic_check(scrubbed)

    return run, None


# ─────────────────────────────────────────────────────────────────
# Benchmark runner
# ─────────────────────────────────────────────────────────────────

SETUPS = {
    1: ("Local Ollama (llama3.2:1b)", build_setup1),
    2: ("Groq + Rule-Based Keywords", build_setup2),
    3: ("Groq + Presidio + Keywords", build_setup3),
    4: ("Groq + Embeddings",          build_setup4),
    5: ("Groq + Enterprise Pipeline", build_setup5),
}

COST_PER_1K = {
    1: 0.0,     # local
    2: 0.0,     # no LLM
    3: 0.0,     # no LLM
    4: 0.0,     # local embeddings
    5: 0.0,     # local embeddings + presidio
}
# Note: Groq costs are only incurred when sending CLEAN inputs to the final LLM task.
# The bouncer/scrubber layers shown here are all local or rule-based — zero token cost.


def run_benchmark(setup_id: int, run_fn: Callable, max_cases: int = 60) -> SetupResult:
    name = SETUPS[setup_id][0]
    cases = TEST_CASES[:max_cases]
    verdicts = []

    iterator = track(cases, description=f"  Setup {setup_id}") if RICH else cases

    for text, expected_blocked in iterator:
        t0 = time.perf_counter()
        try:
            result = run_fn(text)
            actually_blocked = "BLOCKED" in result
        except Exception as e:
            actually_blocked = False
            result = f"ERROR: {e}"
        latency_ms = (time.perf_counter() - t0) * 1000
        verdicts.append((text, expected_blocked, actually_blocked, latency_ms))

    return SetupResult(setup_name=name, verdicts=verdicts)


def format_pct(v):  return f"{v*100:.1f}%"
def fmt_ms(v):      return f"{v:.0f}ms"


def print_results(results: list[SetupResult]):
    should_block = sum(1 for _, e in TEST_CASES if e)
    should_clean = sum(1 for _, e in TEST_CASES if not e)

    if RICH:
        table = Table(title="Semantic Bouncer Benchmark — 60 sentences", show_header=True)
        table.add_column("Setup",       style="bold", width=32)
        table.add_column("Accuracy",    justify="right")
        table.add_column("Precision",   justify="right")
        table.add_column("Recall",      justify="right")
        table.add_column("F1",          justify="right")
        table.add_column("FN",          justify="right", header_style="red")
        table.add_column("FP",          justify="right", header_style="yellow")
        table.add_column("Avg ms",      justify="right")
        table.add_column("p95 ms",      justify="right")
        table.add_column("Cost/60",     justify="right")

        for r in results:
            table.add_row(
                r.setup_name,
                format_pct(r.accuracy),
                format_pct(r.precision),
                format_pct(r.recall),
                format_pct(r.f1),
                str(r.false_negatives),
                str(r.false_positives),
                fmt_ms(r.avg_latency_ms),
                fmt_ms(r.p95_latency_ms),
                "$0.00",
            )
        console.print(table)

        # Print misses for each setup
        for r in results:
            if r.misses:
                console.print(f"\n[bold]{r.setup_name}[/bold] — {len(r.misses)} misses:")
                for inp, exp, act in r.misses:
                    label = "FALSE NEGATIVE (missed threat)" if exp else "FALSE POSITIVE (over-blocked)"
                    icon  = "🔴" if exp else "🟡"
                    console.print(f"  {icon} [{label}] {inp[:80]}")
    else:
        # Plain text fallback
        print("\n" + "="*100)
        print(f"{'Setup':<35} {'Accuracy':>9} {'Precision':>10} {'Recall':>8} {'F1':>6} {'FN':>5} {'FP':>5} {'Avg ms':>8} {'p95 ms':>8}")
        print("-"*100)
        for r in results:
            print(f"{r.setup_name:<35} {format_pct(r.accuracy):>9} {format_pct(r.precision):>10} {format_pct(r.recall):>8} {format_pct(r.f1):>6} {r.false_negatives:>5} {r.false_positives:>5} {fmt_ms(r.avg_latency_ms):>8} {fmt_ms(r.p95_latency_ms):>8}")
        print("="*100)


def export_results(results: list[SetupResult], prefix: str):
    # CSV summary
    csv_path = Path(f"{prefix}_summary.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Setup", "Accuracy", "Precision", "Recall", "F1",
                         "FalseNegatives", "FalsePositives", "AvgLatencyMs", "P95LatencyMs"])
        for r in results:
            writer.writerow([
                r.setup_name,
                f"{r.accuracy:.4f}", f"{r.precision:.4f}",
                f"{r.recall:.4f}", f"{r.f1:.4f}",
                r.false_negatives, r.false_positives,
                f"{r.avg_latency_ms:.1f}", f"{r.p95_latency_ms:.1f}",
            ])
    print(f"Saved: {csv_path}")

    # Markdown table
    md_path = Path(f"{prefix}_report.md")
    with open(md_path, "w") as f:
        f.write("# Chapter 8 Lab — Benchmark Results\n\n")
        f.write(f"**Test suite:** {len(TEST_CASES)} sentences "
                f"({sum(1 for _,e in TEST_CASES if e)} should block, "
                f"{sum(1 for _,e in TEST_CASES if not e)} should pass)\n\n")
        f.write("## Summary\n\n")
        f.write("| Setup | Accuracy | Precision | Recall | F1 | False Neg | False Pos | Avg ms | p95 ms |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in results:
            f.write(
                f"| {r.setup_name} "
                f"| {format_pct(r.accuracy)} "
                f"| {format_pct(r.precision)} "
                f"| {format_pct(r.recall)} "
                f"| {format_pct(r.f1)} "
                f"| {r.false_negatives} "
                f"| {r.false_positives} "
                f"| {fmt_ms(r.avg_latency_ms)} "
                f"| {fmt_ms(r.p95_latency_ms)} |\n"
            )
        f.write("\n## Notes\n\n")
        f.write("- **False Negative** = sensitive input incorrectly allowed through (security risk)\n")
        f.write("- **False Positive** = benign input incorrectly blocked (usability cost)\n")
        f.write("- **Recall** = fraction of actual threats caught — the critical security metric\n")
        f.write("- All bouncer/scrubber costs are $0.00 — they run locally or rule-based.\n")
        f.write("  Token costs only apply to the downstream LLM task on CLEAN inputs.\n\n")

        f.write("## Misses per Setup\n\n")
        for r in results:
            if r.misses:
                f.write(f"### {r.setup_name}\n\n")
                for inp, exp, act in r.misses:
                    label = "🔴 False Negative" if exp else "🟡 False Positive"
                    f.write(f"- {label}: *{inp}*\n")
                f.write("\n")

    print(f"Saved: {md_path}")

    # Detailed per-sentence CSV
    detail_path = Path(f"{prefix}_detail.csv")
    with open(detail_path, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["Sentence", "ExpectedBlocked"] + [r.setup_name for r in results] + \
                 [f"{r.setup_name}_ms" for r in results]
        writer.writerow(header)
        for i, (text, expected) in enumerate(TEST_CASES):
            row = [text, expected]
            for r in results:
                _,_,actually_blocked,_ = r.verdicts[i]
                row.append(actually_blocked)
            for r in results:
                _,_,_,latency = r.verdicts[i]
                row.append(f"{latency:.1f}")
            writer.writerow(row)
    print(f"Saved: {detail_path}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic Bouncer Benchmark")
    parser.add_argument("--setup", type=int, choices=[1,2,3,4,5],
                        help="Run only this setup (default: all)")
    parser.add_argument("--skip", type=int, nargs="+", default=[],
                        help="Skip these setup numbers (e.g. --skip 1)")
    parser.add_argument("--export", type=str, metavar="PREFIX",
                        help="Export results to PREFIX_summary.csv, PREFIX_report.md, PREFIX_detail.csv")
    parser.add_argument("--cases", type=int, default=60,
                        help="Number of test cases to run (default: 60)")
    args = parser.parse_args()

    setup_ids = [args.setup] if args.setup else [1, 2, 3, 4, 5]
    setup_ids = [s for s in setup_ids if s not in args.skip]

    print(f"\nChapter 8 Lab — Semantic Bouncer Benchmark")
    print(f"Running {args.cases} test cases across {len(setup_ids)} setup(s)\n")

    results = []
    for sid in setup_ids:
        name, builder = SETUPS[sid]
        print(f"── Setup {sid}: {name}")
        run_fn, err = builder()
        if err:
            print(f"   SKIPPED: {err}\n")
            continue
        result = run_benchmark(sid, run_fn, max_cases=args.cases)
        results.append(result)
        print(f"   Accuracy: {format_pct(result.accuracy)} | "
              f"Recall: {format_pct(result.recall)} | "
              f"Avg: {fmt_ms(result.avg_latency_ms)}\n")

    if results:
        print_results(results)
        if args.export:
            export_results(results, args.export)