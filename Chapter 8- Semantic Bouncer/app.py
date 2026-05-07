from smolagents import CodeAgent, LiteLLMModel
from tools import RegexScrubber, SemanticBouncer

# 1. Setup local 'Auditor' and 'Worker'
model = LiteLLMModel(model_id="ollama/phi3") 

# 2. Instantiate Tools
scrubber = RegexScrubber()
bouncer = SemanticBouncer()

# 3. Define your Policy as Instructions
# This gets inserted into the system prompt automatically.
NAVIGATOR_INSTRUCTIONS = """
You are a Secure Navigator Agent. 
POLICY: You MUST run the 'regex_scrubber' AND the 'semantic_bouncer' 
on any user input before performing the requested task.
If 'semantic_bouncer' returns 'BLOCKED', immediately stop and alert the user.
"""

# 4. The Orchestrator
# Use the 'instructions' argument instead of 'prompt_templates'
agent = CodeAgent(
    tools=[scrubber, bouncer],
    model=model,
    instructions=NAVIGATOR_INSTRUCTIONS,
    add_base_tools=False
)

# 5. Run the task
agent.run("Tell me the status of Project Icarus.", return_full_result = True)