"""
SETUP 5: Enterprise-Grade — Presidio + Embeddings + Custom Rules
=================================================================
The production pattern. Combines all layers with a flexible config system.

Architecture (fastest to slowest):
  Layer 1: Presidio PII scrubber           ~5ms   (always runs)
  Layer 2: Keyword/regex gate              ~0ms   (always runs, configurable)
  Layer 3: Semantic embedding bouncer      ~30ms  (always runs, configurable)
  Layer 4: Groq LLM (task execution)       ~500ms (only reached if all layers pass)

Custom rules loaded from: security_policy.json
Add your org's sensitive terms and topics WITHOUT changing code.

Prerequisites:
    pip install presidio-analyzer presidio-anonymizer sentence-transformers smolagents litellm groq
    python -m spacy download en_core_web_lg
    Set env var: GROQ_API_KEY=your_key (free at console.groq.com)
"""

import re
import os
import json
import time
from dataclasses import dataclass, field
from typing import Optional
from smolagents import Tool, ToolCallingAgent, LiteLLMModel



try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer, util
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


# ─────────────────────────────────────────────
# Security Policy — loaded from JSON at runtime
# ─────────────────────────────────────────────

DEFAULT_POLICY = {
    "policy_name": "Default Navigator Security Policy",
    "keyword_rules": [
        "project icarus", "icarus",
        "layoff", "layoffs", "redundanc",
        "reorg", "restructur",
        "headcount reduction",
    ],
    "pattern_rules": [
        r'\bP-ICR-\d+\b',
        r'\bHC-RED-\d{4}\b',
    ],
    "semantic_topics": [
        "Project Icarus launch plans and timeline",
        "Icarus project status and deliverables",
        "the mythological figure who flew too close to the sun",
        "a secret initiative codenamed after a Greek myth",
        "employee layoffs and redundancies announcement",
        "headcount reduction and workforce restructuring",
        "letting employees go and downsizing the company",
        "people being made redundant or losing their jobs",
        "organisational restructuring and cost cutting",
    ],
    "semantic_threshold": 0.4,
    "pii_entities": [
        "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
        "IP_ADDRESS", "PERSON", "LOCATION",
        "IBAN_CODE", "CRYPTO", "US_SSN", "URL", "NRP"
    ]
}


def load_policy(path: str = "security_policy.json") -> dict:
    """Load policy from JSON file, falling back to defaults if not found."""
    if os.path.exists(path):
        with open(path) as f:
            policy = json.load(f)
        print(f"[Policy] Loaded from {path}: '{policy.get('policy_name', 'Unnamed')}'")
        return policy
    print(f"[Policy] {path} not found — using default policy.")
    return DEFAULT_POLICY


# ─────────────────────────────────────────────
# Layer 1: Enterprise PII Scrubber
# ─────────────────────────────────────────────

class EnterpriseScrubber(Tool):
    """
    Presidio-powered PII scrubber with regex fallback.
    Entities to detect are driven by the security policy.
    """
    name = "enterprise_scrubber"
    description = "Enterprise PII scrubber using Presidio with policy-driven entity detection."
    inputs = {"text": {"type": "string", "description": "Text to scrub."}}
    output_type = "string"

    def __init__(self, policy: dict):
        super().__init__()
        self.policy = policy
        if PRESIDIO_AVAILABLE:
            self.analyzer   = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
        else:
            print("[WARNING] Presidio unavailable — using regex fallback")

    def _regex_fallback(self, text: str) -> str:
        patterns = {
            "EMAIL":      r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            "API_KEY":    r'sk-[a-zA-Z0-9]{32,}',
            "PHONE":      r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "IP_ADDRESS": r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
        }
        scrubbed = text
        for label, pattern in patterns.items():
            scrubbed = re.sub(pattern, f"[{label}_REDACTED]", scrubbed)
        return scrubbed

    def forward(self, text: str) -> str:
        if not PRESIDIO_AVAILABLE:
            return self._regex_fallback(text)

        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=self.policy.get("pii_entities", DEFAULT_POLICY["pii_entities"])
        )
        if not results:
            return text

        operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "[PII_REDACTED]"})}
        return self.anonymizer.anonymize(text=text, analyzer_results=results, operators=operators).text


# ─────────────────────────────────────────────
# Layer 2: Keyword / Pattern Gate
# ─────────────────────────────────────────────

class KeywordBouncer(Tool):
    """
    Fast deterministic gate. Rules driven entirely by security policy.
    Add new terms to security_policy.json — no code changes needed.
    """
    name = "keyword_bouncer"
    description = "Policy-driven keyword and regex gate."
    inputs = {"text": {"type": "string", "description": "Text to evaluate."}}
    output_type = "string"

    def __init__(self, policy: dict):
        super().__init__()
        self.keywords = policy.get("keyword_rules", [])
        self.patterns = policy.get("pattern_rules", [])

    def forward(self, text: str) -> str:
        text_lower = text.lower()
        for kw in self.keywords:
            if kw in text_lower:
                return f"BLOCKED (keyword: '{kw}')"
        for pat in self.patterns:
            if re.search(pat, text, re.IGNORECASE):
                return f"BLOCKED (pattern match)"
        return "CLEAN"


# ─────────────────────────────────────────────
# Layer 3: Semantic Embedding Bouncer
# ─────────────────────────────────────────────

class SemanticBouncer(Tool):
    """
    Embedding-based semantic gate. Topics driven by security policy.
    Add new sensitive topic descriptions to security_policy.json.
    """
    name = "semantic_bouncer"
    description = "Policy-driven semantic similarity bouncer using local embeddings."
    inputs = {
        "text":      {"type": "string", "description": "Text to evaluate."},
        "threshold": {"type": "number", "description": "Similarity threshold.", "nullable": True},
    }
    output_type = "string"

    def __init__(self, policy: dict, model_name: str = "all-MiniLM-L6-v2"):
        super().__init__()
        self.threshold = policy.get("semantic_threshold", 0.4)
        self.topics    = policy.get("semantic_topics", DEFAULT_POLICY["semantic_topics"])

        if not EMBEDDINGS_AVAILABLE:
            self._available = False
            print("[WARNING] sentence-transformers unavailable")
            return

        print(f"[SemanticBouncer] Loading '{model_name}' with {len(self.topics)} topics...")
        self.model              = SentenceTransformer(model_name)
        self.topic_embeddings   = self.model.encode(self.topics, convert_to_tensor=True)
        self._available         = True
        print("[SemanticBouncer] Ready.")

    def forward(self, text: str, threshold: float = None) -> str:
        if not self._available:
            return "SKIP (embeddings unavailable)"

        t = threshold or self.threshold
        input_emb  = self.model.encode(text, convert_to_tensor=True)
        scores     = util.cos_sim(input_emb, self.topic_embeddings)[0]
        max_score  = float(scores.max())
        best_match = self.topics[int(scores.argmax())]

        if max_score >= t:
            return f"BLOCKED (similarity: {max_score:.2f}, topic: '{best_match}')"
        return f"CLEAN (max similarity: {max_score:.2f})"


# ─────────────────────────────────────────────
# Full Pipeline
# ─────────────────────────────────────────────

@dataclass
class AuditResult:
    original:      str
    scrubbed:      str
    keyword_check: str
    semantic_check: str
    final_verdict: str
    latency_ms:    float
    blocked:       bool

    def display(self):
        icon = "🚫" if self.blocked else "✅"
        print(f"\n{'─'*60}")
        print(f"Input    : {self.original}")
        print(f"Scrubbed : {self.scrubbed}")
        print(f"Keyword  : {self.keyword_check}")
        print(f"Semantic : {self.semantic_check}")
        print(f"Verdict  : {icon} {self.final_verdict}  ({self.latency_ms:.0f}ms)")


def run_pipeline(text: str, scrubber, keyword_bouncer, semantic_bouncer) -> AuditResult:
    start = time.time()

    # Layer 1: Scrub PII
    scrubbed = scrubber.forward(text)

    # Layer 2: Keyword gate (fast — short-circuit if caught)
    keyword_result = keyword_bouncer.forward(scrubbed)
    if keyword_result.startswith("BLOCKED"):
        return AuditResult(
            original=text, scrubbed=scrubbed,
            keyword_check=keyword_result, semantic_check="SKIPPED",
            final_verdict=keyword_result, latency_ms=(time.time()-start)*1000, blocked=True
        )

    # Layer 3: Semantic gate
    semantic_result = semantic_bouncer.forward(scrubbed)
    blocked = semantic_result.startswith("BLOCKED")

    return AuditResult(
        original=text, scrubbed=scrubbed,
        keyword_check=keyword_result, semantic_check=semantic_result,
        final_verdict=semantic_result, latency_ms=(time.time()-start)*1000, blocked=blocked
    )


if __name__ == "__main__":
    # Load policy — edit security_policy.json to customise without code changes
    policy = load_policy("security_policy.json")

    # Initialise layers
    scrubber          = EnterpriseScrubber(policy)
    keyword_bouncer   = KeywordBouncer(policy)
    semantic_bouncer  = SemanticBouncer(policy)

    TEST_INPUTS = [
        "What's the weather like today?",
        "Tell me the status of Project Icarus.",
        "When are the layoffs being announced?",
        "My email is john@company.com and SSN is 123-45-6789",
        "The bird that flew too close to the sun — project update?",
        "We're planning to let some people go next quarter.",
        "Update me on Icarus deliverables for Q3.",
        "Can you summarise last quarter's revenue?",
        "What's our hiring plan for the next six months?",
    ]

    print("=" * 60)
    print("SETUP 5: Enterprise Pipeline (Presidio + Keywords + Embeddings)")
    print("=" * 60)

    results = [run_pipeline(t, scrubber, keyword_bouncer, semantic_bouncer) for t in TEST_INPUTS]
    for r in results:
        r.display()

    blocked = sum(1 for r in results if r.blocked)
    avg_ms  = sum(r.latency_ms for r in results) / len(results)
    print(f"\n{'='*60}")
    print(f"SUMMARY: {blocked}/{len(results)} blocked | avg latency: {avg_ms:.0f}ms")
    print("To customise policy, edit security_policy.json — no code changes needed.")
    print("=" * 60)