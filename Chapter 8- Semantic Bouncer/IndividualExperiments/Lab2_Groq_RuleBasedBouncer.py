"""
SETUP 2: Groq + Rule-Based Bouncer
====================================
Swap local Ollama for Groq (free, fast) as the reasoning engine.
Replace LLM-based bouncer with a deterministic keyword/rule gate.

WHY: For KNOWN sensitive terms, you don't need an LLM at all.
Deterministic rules are faster, cheaper, and more reliable.

Prerequisites:
    pip install smolagents litellm groq
    Set env var: GROQ_API_KEY=your_key (free at console.groq.com)
"""

import re
import os
from smolagents import Tool, ToolCallingAgent, LiteLLMModel


class RegexScrubber(Tool):
    name = "regex_scrubber"
    description = "Removes standard PII like emails, API keys, and phone numbers using regex."
    inputs = {
        "text": {
            "type": "string",
            "description": "The raw user input to be scrubbed of basic PII.",
        }
    }
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


class RuleBasedBouncer(Tool):
    """
    Deterministic keyword + pattern gate.
    No LLM involved — instant, zero cost, 100% reliable for KNOWN terms.
    Limitation: Cannot catch novel phrasing or metaphorical references.
    """
    name = "rule_based_bouncer"
    description = "Blocks inputs containing known sensitive keywords or patterns."
    inputs = {
        "text": {
            "type": "string",
            "description": "Text to evaluate against security rules.",
        }
    }
    output_type = "string"

    # Add your organisation's sensitive terms here
    BLOCKED_KEYWORDS = [
        "project icarus", "icarus",
        "layoff", "layoffs", "redundanc",
        "reorg", "restructur",
        "headcount reduction",
    ]

    # Regex patterns for structured sensitive data
    BLOCKED_PATTERNS = [
        r'\bP-ICR-\d+\b',          # Internal Icarus ticket IDs
        r'\bHC-RED-\d{4}\b',       # Headcount reduction codes
    ]

    def forward(self, text: str) -> str:
        text_lower = text.lower()

        # Check keywords
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in text_lower:
                return f"BLOCKED (keyword: '{keyword}')"

        # Check patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return f"BLOCKED (pattern match)"

        return "CLEAN"


def secure_pipeline(user_input: str, scrubber, bouncer) -> str:
    """Direct pipeline — no agent loop, no LLM orchestration overhead."""
    scrubbed = scrubber.forward(user_input)
    verdict  = bouncer.forward(scrubbed)

    if verdict.startswith("BLOCKED"):
        return f"🚫 {verdict}"

    # Only reach here if CLEAN — safe to pass to Groq
    return f"✅ CLEAN — sending to LLM: '{scrubbed}'"


if __name__ == "__main__":
    scrubber = RegexScrubber()
    bouncer  = RuleBasedBouncer()

    TEST_INPUTS = [
        "What's the weather like today?",
        "Tell me the status of Project Icarus.",
        "When are the layoffs being announced?",
        "My email is john@company.com",
        "Update me on Icarus deliverables for Q3.",
        "Can you summarise last quarter's revenue?",
        "The bird that flew too close to the sun — project update?",  # Evades keyword gate
    ]

    print("=" * 60)
    print("SETUP 2: Groq + Rule-Based Bouncer")
    print("EXPECTED: Known keywords blocked. Metaphors slip through.")
    print("=" * 60)

    for user_input in TEST_INPUTS:
        result = secure_pipeline(user_input, scrubber, bouncer)
        print(f"\nInput : {user_input}")
        print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("LIMITATION: 'the bird that flew too close to the sun' → CLEAN")
    print("Keyword gates are blind to semantic/metaphorical references.")
    print("=" * 60)