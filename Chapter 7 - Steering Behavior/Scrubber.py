import re
from typing import List, Dict, Tuple
from pydantic import BaseModel, Field
from loguru import logger

class ScrubbingReport(BaseModel):
    """Telemetry data for the Lab audit pass."""
    found_pii: bool
    patterns_matched: List[str]
    redacted_count: int

class SovereignScrubber:
    """
    THE ENTERPRISE GATEWAY WRAPPER (CORE ENGINE)
    Designed to be modular: New PII types can be added to self.registry without 
    changing the redact() logic.
    """
    def __init__(self, custom_patterns: Dict[str, str] = None):
        # Default Enterprise Pattern Registry
        self.registry = {
            "EMAIL": r"[\w\.-]+@[\w\.-]+\.\w+",
            "PHONE": r"\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
            "API_KEY": r"(sk|AIza|ghp|gho|ghs|ghr|ght)_[a-zA-Z0-9]{32,}",
            "CREDIT_CARD": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
            "IPV4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        }
        if custom_patterns:
            self.registry.update(custom_patterns)

    def add_pattern(self, label: str, regex: str):
        """Modular extension: Add new PII types (e.g., SSN, Passport) on the fly."""
        self.registry[label] = regex
        logger.info(f"Registry Updated: Added detector for {label}")

    def redact(self, text: str, mode: str = "generic") -> Tuple[str, ScrubbingReport]:
        """
        Executes the 'Physical Gate' pass.
        - generic: [REDACTED_TYPE]
        - coding:  [VAR_TYPE_INDEX]
        """
        matches_found = []
        redacted_text = text
        total_count = 0

        for label, pattern in self.registry.items():
            matches = re.findall(pattern, text)
            if matches:
                matches_found.append(label)
                for i, match in enumerate(matches, 1):
                    total_count += 1
                    # Choose replacement style based on use-case nuance
                    replacement = f"[REDACTED_{label}]" if mode == "generic" else f"[VAR_{label}_{i}]"
                    # We use re.escape(match) to ensure special characters in the PII don't break regex
                    redacted_text = redacted_text.replace(match, replacement)

        report = ScrubbingReport(
            found_pii=bool(matches_found),
            patterns_matched=list(set(matches_found)),
            redacted_count=total_count
        )
        return redacted_text, report