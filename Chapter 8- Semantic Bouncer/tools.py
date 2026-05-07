import re
import ollama
from smolagents import Tool

class RegexScrubber(Tool):
    name = "regex_scrubber"
    description = "A fast, deterministic scrubber that removes standard PII like emails, API keys, and phone numbers using pattern matching."
    inputs = {
        "text": {
            "type": "string",
            "description": "The raw user input to be scrubbed of basic PII.",
        }
    }
    output_type = "string"

    def forward(self, text: str) -> str:
        # Define common PII patterns
        patterns = {
            "EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            "API_KEY": r'sk-[a-zA-Z0-9]{32,}', # Matches common 'sk-' style keys
            "PHONE": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "IP_ADDRESS": r'\b\d{1,3}(?:\.\d{1,3}){3}\b'
        }
        
        scrubbed_text = text
        for label, pattern in patterns.items():
            scrubbed_text = re.sub(pattern, f"[{label}_REDACTED]", scrubbed_text)
            
        return scrubbed_text

class SemanticBouncer(Tool):
    name = "semantic_bouncer"
    description = "A local security auditor that identifies mentions of secret projects or high-risk internal strategies using an SLM."
    inputs = {
        "text": {
            "type": "string",
            "description": "The text to evaluate for contextual security leaks.",
        },
        "target_model": {
            "type": "string",
            "description": "The Ollama model to use for the audit (e.g., 'phi3', 'qwen', 'llama3.2:1b').",
            "nullable": True, # <--- This is the missing piece
        }
    }
    output_type = "string"

    def forward(self, text: str, target_model: str = "phi3") -> str:
        # If target_model comes in as None from the agent, default back to phi3
        model_name = target_model if target_model else "phi3"
        
        system_prompt = (
            "You are a Corporate Security Auditor. Analyze the input for mentions of "
            "PROJECT_ICARUS or proprietary layoff strategies. "
            "Respond ONLY with 'BLOCKED' or 'CLEAN'."
        )
        
        try:
            response = ollama.generate(
                model=model_name, 
                prompt=f"{system_prompt}\n\nInput: {text}"
            )
            verdict = response['response'].strip().upper()
            return "BLOCKED" if "BLOCKED" in verdict else "CLEAN"
        except Exception as e:
            return f"ERROR: {str(e)}"