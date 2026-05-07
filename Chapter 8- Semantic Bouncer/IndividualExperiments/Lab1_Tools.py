"""
SETUP 1: Local Ollama + Small Model
====================================
The 'naive' approach - runs everything locally on consumer hardware.
EXPECTED RESULT: SemanticBouncer returns CLEAN for everything.
This demonstrates WHY small models fail at security-critical classification.
"""

import re
import ollama
from smolagents import Tool


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


class SemanticBouncer(Tool):
    name = "semantic_bouncer"
    description = "Uses a local SLM to detect mentions of secret projects or sensitive strategies."
    inputs = {
        "text": {
            "type": "string",
            "description": "Text to evaluate for security leaks.",
        },
        "target_model": {
            "type": "string",
            "description": "Ollama model to use (e.g. 'llama3.2:1b').",
            "nullable": True,
        }
    }
    output_type = "string"

    def forward(self, text: str, target_model: str = "llama3.2:1b") -> str:
        model_name = target_model or "llama3.2:1b"

        system_prompt = (
            "You are a Corporate Security Auditor. "
            "Analyze the input for mentions of PROJECT_ICARUS or proprietary layoff strategies. "
            "Respond ONLY with 'BLOCKED' or 'CLEAN'."
        )

        try:
            response = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": text[:500]},
                ],
                options={
                    "num_predict": 5,
                    "temperature": 0.0,
                    "num_ctx": 512,
                }
            )
            verdict = response["message"]["content"].strip().upper()
            return "BLOCKED" if "BLOCKED" in verdict else "CLEAN"

        except ollama.ResponseError:
            return f"ERROR: Model '{model_name}' not found. Run: ollama pull {model_name}"
        except Exception as e:
            return f"ERROR: {e}"