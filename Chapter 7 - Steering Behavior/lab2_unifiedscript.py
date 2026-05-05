import os
import sys
from typing import TypedDict, List, Optional
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.table import Table
from langgraph.graph import StateGraph, END
from Scrubber import SovereignScrubber


"""
ENTERPRISE ADOPTION: CHAPTER 7 DUAL-LOCK GATEWAY
------------------------------------------------
1. ARCHITECTURE: This circuit decouples 'Safety' from 'Generation.' By running 
   the Sovereign Scrubber locally, we maintain a Zero-Trust posture with 
   Third-Party Model Providers.

2. STEERING VS. AUDITING: We prioritize 'Steering' (Gate 2) for real-time 
   enforcement to minimize latency. The 'Audit Gate' is designed for 
   sampling—using more powerful LLMs to perform async quality checks and 
   build a robust observability dataset.

3. SCALABILITY: Orchestration via LangGraph allows for 'Worker' nodes to be 
   swapped or upgraded without breaking the safety wrapper. This provides 
   long-term resilience against model deprecation.

4. OBSERVABILITY ROI: The outcome of the Audit Gate should be piped to 
   monitoring tools (Grafana/Datadog) to calculate 'Logic Drift' over time, 
   transforming AI performance from a 'vibe' into a metric.
"""

# 1. LAB SETUP
load_dotenv()
scrubber = SovereignScrubber()
console = Console()

# 2. LOG SUPPRESSION: Quiet the background noise
logger.remove()
logger.add(sys.stderr, level="SUCCESS")

# 3. STATE DEFINITION
class NavigatorState(TypedDict):
    raw_input: str
    clean_input: str
    violated_vectors: List[str]
    safety_status: str      # PASS / BLOCK
    faithfulness_score: float
    worker_output: Optional[str]

# 4. HELPER: Clean Truncation
def truncate(text: str, limit: int = 70) -> str:
    return (text[:limit] + "...") if len(text) > limit else text

# --- NODES ---

def sovereign_gate_node(state: NavigatorState):
    """LOCK 1: Privacy."""
    clean_text, report = scrubber.redact(state['raw_input'])
    return {
        "clean_input": clean_text, 
        "violated_vectors": report.patterns_matched
    }

def bouncer_node(state: NavigatorState):
    """LOCK 2: Steering."""
    # Logic: If a high-risk vector like API_KEY or CREDIT_CARD is found, BLOCK.
    high_risk = {"API_KEY", "CREDIT_CARD"}
    if any(v in high_risk for v in state['violated_vectors']):
        return {"safety_status": "BLOCK"}
    return {"safety_status": "PASS"}

def auditor_node(state: NavigatorState):
    """LOCK 3: Verification."""
    # Placeholder for DeepEval logic from Lab 3
    return {"faithfulness_score": 0.98}

# --- ORCHESTRATION ---

builder = StateGraph(NavigatorState)
builder.add_node("privacy_gate", sovereign_gate_node)
builder.add_node("steering_gate", bouncer_node)
builder.add_node("audit_gate", auditor_node)

builder.set_entry_point("privacy_gate")
builder.add_edge("privacy_gate", "steering_gate")

# Condition: Only audit if the intent passed the steering gate
builder.add_conditional_edges("steering_gate", 
    lambda x: "verify" if x["safety_status"] == "PASS" else "stop",
    {"verify": "audit_gate", "stop": END}
)
builder.add_edge("audit_gate", END)
app = builder.compile()

# --- BATCH EXECUTION ---

def run_batch_lab():
    specimen_path = "lab_specimens.txt"
    if not os.path.exists(specimen_path):
        logger.error(f"Specimen file missing: {specimen_path}")
        return

    table = Table(title="🛡️ THE NAVIGATOR: TRIPLE-LOCK GATEWAY AUDIT", show_lines=True)
    table.add_column("Original Intent", style="cyan", width=75)
    table.add_column("Redacted Output", style="green", width=75)
    table.add_column("Violations", style="magenta", width=30)
    table.add_column("Status", justify="center", width=10)

    with open(specimen_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            # Execute the full graph
            result = app.invoke({"raw_input": line})
            
            # Map state to Table
            clean_text = result.get('clean_input', 'N/A')
            vectors = ", ".join(result.get('violated_vectors', [])) or "NONE"
            status = "✅ PASS" if result.get('safety_status') == "PASS" else "❌ BLOCK"

            table.add_row(truncate(line), truncate(clean_text), vectors, status)

    console.print(table)
    logger.success("Batch Triple-Lock Audit Complete.")

if __name__ == "__main__":
    run_batch_lab()