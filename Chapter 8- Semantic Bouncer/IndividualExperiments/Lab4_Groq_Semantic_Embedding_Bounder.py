"""
SETUP 4: Groq + Semantic Embedding Bouncer
==========================================
Replace keyword matching with semantic similarity using sentence embeddings.
A local 80MB model converts text to vectors — similar meaning = similar vector.

This catches:
  - "the bird that flew too close to the sun" → BLOCKED (Icarus reference)
  - "we're letting people go next quarter" → BLOCKED (layoff reference)
  - Novel phrasing the keyword list never anticipated

The embedding model runs fully locally — sensitive text never leaves your machine.
Groq is only used for the final LLM task on CLEAN inputs.

Prerequisites:
    pip install sentence-transformers smolagents litellm groq
    Set env var: GROQ_API_KEY=your_key (free at console.groq.com)

Note: First run downloads ~80MB model. Subsequent runs use cache.
"""

import re
import os
import numpy as np
from smolagents import Tool


try:
    from sentence_transformers import SentenceTransformer, util
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("[WARNING] sentence-transformers not installed.")
    print("[WARNING] Run: pip install sentence-transformers")


class RegexScrubber(Tool):
    name = "regex_scrubber"
    description = "Removes standard PII using regex patterns."
    inputs = {"text": {"type": "string", "description": "Text to scrub."}}
    output_type = "string"

    def forward(self, text: str) -> str:
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


class EmbeddingBouncer(Tool):
    """
    Semantic similarity bouncer using sentence-transformers.

    How it works:
    1. At init, embed a library of 'sensitive topic' descriptions into vectors
    2. At runtime, embed the input text into a vector
    3. Compute cosine similarity between input and every sensitive topic
    4. If max similarity > threshold → BLOCKED

    The model (all-MiniLM-L6-v2) is only 80MB and runs on CPU.
    Inference is ~10-50ms — faster than any LLM call.
    """
    name = "embedding_bouncer"
    description = "Blocks inputs semantically similar to known sensitive topics using local embeddings."
    inputs = {
        "text": {
            "type": "string",
            "description": "Text to evaluate for semantic similarity to sensitive topics.",
        },
        "threshold": {
            "type": "number",
            "description": "Similarity threshold 0-1. Higher = stricter. Default 0.4.",
            "nullable": True,
        }
    }
    output_type = "string"

    # Describe sensitive topics in plain English — the more descriptions, the better coverage
    SENSITIVE_TOPICS = [
        # Project Icarus variants
        "Project Icarus launch plans and timeline",
        "Icarus project status and deliverables",
        "the mythological figure who flew too close to the sun",
        "a secret initiative codenamed after a Greek myth",
        "confidential product launch under a codename",

        # Layoff / restructuring variants
        "employee layoffs and redundancies announcement",
        "headcount reduction and workforce restructuring",
        "letting employees go and downsizing the company",
        "people being made redundant or losing their jobs",
        "organisational restructuring and cost cutting",
        "reduction in force and severance packages",
    ]

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        super().__init__()
        if not EMBEDDINGS_AVAILABLE:
            self._available = False
            return

        print(f"[EmbeddingBouncer] Loading model '{model_name}'...")
        self.model = SentenceTransformer(model_name)
        self.sensitive_embeddings = self.model.encode(
            self.SENSITIVE_TOPICS,
            convert_to_tensor=True
        )
        self._available = True
        print(f"[EmbeddingBouncer] Ready. {len(self.SENSITIVE_TOPICS)} sensitive topics loaded.")

    def forward(self, text: str, threshold: float = 0.4) -> str:
        if not self._available:
            return "ERROR: sentence-transformers not installed"

        threshold = threshold or 0.4

        # Embed the input
        input_embedding = self.model.encode(text, convert_to_tensor=True)

        # Compare against all sensitive topics
        scores = util.cos_sim(input_embedding, self.sensitive_embeddings)[0]
        max_score   = float(scores.max())
        best_match  = self.SENSITIVE_TOPICS[int(scores.argmax())]

        if max_score >= threshold:
            return f"BLOCKED (similarity: {max_score:.2f}, matched topic: '{best_match}')"

        return f"CLEAN (max similarity: {max_score:.2f})"


def secure_pipeline(user_input: str, scrubber, bouncer, threshold: float = 0.4) -> str:
    scrubbed = scrubber.forward(user_input)
    verdict  = bouncer.forward(scrubbed, threshold=threshold)
    if verdict.startswith("BLOCKED"):
        return f"🚫 {verdict}"
    return f"✅ {verdict}"


if __name__ == "__main__":
    scrubber = RegexScrubber()
    bouncer  = EmbeddingBouncer()

    TEST_INPUTS = [
        ("What's the weather like today?",                        "CLEAN"),
        ("Tell me the status of Project Icarus.",                 "BLOCKED"),
        ("When are the layoffs being announced?",                 "BLOCKED"),
        ("Update me on Icarus deliverables for Q3.",              "BLOCKED"),
        ("The bird that flew too close to the sun — update?",     "BLOCKED"),  # Now caught!
        ("We're planning to let some people go next quarter.",    "BLOCKED"),  # Now caught!
        ("Can you summarise last quarter's revenue?",             "CLEAN"),
        ("What's our hiring plan for the next six months?",       "CLEAN"),
    ]

    print("=" * 60)
    print("SETUP 4: Groq + Semantic Embedding Bouncer")
    print("EXPECTED: Metaphors and novel phrasing now caught.")
    print("=" * 60)

    correct = 0
    for user_input, expected in TEST_INPUTS:
        result   = secure_pipeline(user_input, scrubber, bouncer)
        actual   = "BLOCKED" if result.startswith("🚫") else "CLEAN"
        match    = "✓" if actual == expected else "✗ WRONG"
        correct += 1 if actual == expected else 0

        print(f"\nInput   : {user_input}")
        print(f"Expected: {expected} | Got: {actual} {match}")
        print(f"Detail  : {result}")

    print(f"\n{'=' * 60}")
    print(f"ACCURACY: {correct}/{len(TEST_INPUTS)} correct")
    print("UPGRADE: Semantic matching catches phrasing keyword lists miss.")
    print("=" * 60)