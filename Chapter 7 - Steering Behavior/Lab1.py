from loguru import logger
from Scrubber import SovereignScrubber
import re

def enterprise_inference_wrapper(raw_user_input: str):
    """
    ENTERPRISE ADOPTION NOTE:
    This function represents the 'Middleware Wrapper'. In a production environment:
    1. REGULATORY: This runs in a VPC (Virtual Private Cloud) before the data hits the public internet.
    2. OBSERVABILITY: Every 'ScrubbingReport' is sent to a SIEM (like Splunk) for compliance auditing.
    3. PERFORMANCE: Regex is O(n). For 2M token context windows, ensure this is optimized or 
       chunked to prevent 'Time to First Token' (TTFT) latency issues.
    """
    scrubber = SovereignScrubber()
    
    # Example: Easily adding a new internal PII type for a specific department
    scrubber.add_pattern("INTERNAL_ID", r"NAV-[0-9]{5}")

    # --- THE LAB SPECIMEN ---
    logger.info("🧪 INITIALIZING LABORATORY TEST: PII GATING")
    
    # DATA COLLECTION: Execute the deterministic gate
    sanitized_text, report = scrubber.redact(raw_user_input, mode="generic")

    # --- ASSERTION SUITE: THE CIRCUIT BREAKER ---
    # These assertions verify the integrity of the wrapper before 'Broadcast'
    try:
        # Assertion 1: Total Erasure. No 'radioactive' patterns should remain.
        for label, regex in scrubber.registry.items():
            assert not re.search(regex, sanitized_text), f"🚨 CRITICAL LEAK: {label} found in output!"
        
        # Assertion 2: Metadata Fidelity. Did we catch what we expected?
        if report.found_pii:
            assert "[REDACTED_" in sanitized_text, "🚨 LOGIC ERROR: PII flagged but not replaced."
            logger.info(f"Audit Summary: Found {report.redacted_count} leaks across {report.patterns_matched}")

        logger.success("✅ WRAPPER INTEGRITY VERIFIED: Safe for LLM Broadcast.")
        return sanitized_text

    except AssertionError as e:
        # CIRCUIT BREAKER: Stop the request. Do not call the LLM API.
        logger.error(f"🛑 GATEWAY SHUTDOWN: {e}")
        return None

if __name__ == "__main__":
    # Test Case: Messy input with mixed PII and a new Internal ID
    sample = "Admin: John (j.doe@work.com) check ID NAV-12345. Key: sk-998877665544332211"
    final_output = enterprise_inference_wrapper(sample)
    
    if final_output:
        print(f"\nBroadcast Ready Output:\n{final_output}")