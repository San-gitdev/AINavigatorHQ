"""
SETUP 3: Groq + Microsoft Presidio (Enterprise PII Scrubbing)
==============================================================
Replace regex scrubber with Microsoft Presidio — the open-source PII engine
used in enterprise/banking environments. Detects 50+ entity types including
jurisdiction-specific ones (NHS numbers, EU IBANs, passports, etc.)

Presidio uses NLP (spaCy) under the hood — far more accurate than regex alone.

Prerequisites:
    pip install presidio-analyzer presidio-anonymizer
    python -m spacy download en_core_web_lg
    pip install smolagents litellm groq
    Set env var: GROQ_API_KEY=your_key (free at console.groq.com)
"""

import re
import os
from smolagents import Tool, ToolCallingAgent, LiteLLMModel


# Presidio imports
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


class PresidioPIIScrubber(Tool):
    """
    Enterprise-grade PII scrubber using Microsoft Presidio.
    Detects 50+ entity types using NLP, not just regex.

    Detected types include:
    - Standard: EMAIL, PHONE, CREDIT_CARD, IP_ADDRESS, URL
    - Identity: PERSON, NRP (National Registration), PASSPORT, DRIVER_LICENSE
    - Financial: IBAN_CODE, CRYPTO, US_BANK_NUMBER, US_SSN
    - Medical: US_HEALTHCARE_NPI, MEDICAL_LICENSE
    - Location: LOCATION, ADDRESS
    """
    name = "presidio_pii_scrubber"
    description = "Enterprise-grade PII scrubber using Microsoft Presidio. Detects 50+ entity types."
    inputs = {
        "text": {
            "type": "string",
            "description": "Raw text to scrub of PII.",
        }
    }
    output_type = "string"

    def __init__(self):
        super().__init__()
        try:
            self.analyzer  = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self._available = True
        except Exception as e:
            print(f"[WARNING] Presidio not available: {e}")
            print("[WARNING] Falling back to regex scrubber.")
            self._available = False

    def _regex_fallback(self, text: str) -> str:
        """Fallback if Presidio isn't installed."""
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
        if not self._available:
            return self._regex_fallback(text)

        # Detect PII
        results = self.analyzer.analyze(
            text=text,
            language="en",
            # Specify entities to detect — or omit to detect all
            entities=[
                "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
                "IP_ADDRESS", "PERSON", "LOCATION",
                "IBAN_CODE", "CRYPTO", "US_SSN",
                "URL", "NRP",
            ]
        )

        if not results:
            return text  # Nothing found

        # Anonymize with clear labels
        operators = {
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
            "PHONE_NUMBER":  OperatorConfig("replace", {"new_value": "[PHONE_REDACTED]"}),
            "PERSON":        OperatorConfig("replace", {"new_value": "[PERSON_REDACTED]"}),
            "CREDIT_CARD":   OperatorConfig("replace", {"new_value": "[CC_REDACTED]"}),
            "LOCATION":      OperatorConfig("replace", {"new_value": "[LOCATION_REDACTED]"}),
            "US_SSN":        OperatorConfig("replace", {"new_value": "[SSN_REDACTED]"}),
            "IBAN_CODE":     OperatorConfig("replace", {"new_value": "[IBAN_REDACTED]"}),
            "DEFAULT":       OperatorConfig("replace", {"new_value": "[PII_REDACTED]"}),
        }

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text


class RuleBasedBouncer(Tool):
    """Same as Setup 2 — deterministic keyword gate."""
    name = "rule_based_bouncer"
    description = "Blocks inputs containing known sensitive keywords or patterns."
    inputs = {
        "text": {"type": "string", "description": "Text to evaluate."}
    }
    output_type = "string"

    BLOCKED_KEYWORDS = [
        "project icarus", "icarus",
        "layoff", "layoffs", "redundanc",
        "reorg", "restructur",
        "headcount reduction",
    ]

    BLOCKED_PATTERNS = [
        r'\bP-ICR-\d+\b',
        r'\bHC-RED-\d{4}\b',
    ]

    def forward(self, text: str) -> str:
        text_lower = text.lower()
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in text_lower:
                return f"BLOCKED (keyword: '{keyword}')"
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return f"BLOCKED (pattern match)"
        return "CLEAN"


def secure_pipeline(user_input: str, scrubber, bouncer) -> str:
    scrubbed = scrubber.forward(user_input)
    verdict  = bouncer.forward(scrubbed)
    if verdict.startswith("BLOCKED"):
        return f"🚫 {verdict}"
    return f"✅ CLEAN — sending to LLM: '{scrubbed}'"


if __name__ == "__main__":
    scrubber = PresidioPIIScrubber()
    bouncer  = RuleBasedBouncer()

    TEST_INPUTS = [
        "What's the weather like today?",
        "Tell me the status of Project Icarus.",
        "My name is John Smith and my email is john@company.com, SSN 123-45-6789",
        "Call me at 555-867-5309, my IBAN is GB29NWBK60161331926819",
        "When are the layoffs being announced?",
        "Update me on Icarus deliverables for Q3.",
        "The bird that flew too close to the sun — project update?",  # Still evades
    ]

    print("=" * 60)
    print("SETUP 3: Groq + Microsoft Presidio PII Scrubber")
    print("EXPECTED: Much richer PII detection. Bouncer still keyword-based.")
    print("=" * 60)

    for user_input in TEST_INPUTS:
        result = secure_pipeline(user_input, scrubber, bouncer)
        print(f"\nInput : {user_input}")
        print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("UPGRADE: PII detection is now enterprise-grade.")
    print("GAP: Semantic/metaphorical references still slip through.")
    print("=" * 60)