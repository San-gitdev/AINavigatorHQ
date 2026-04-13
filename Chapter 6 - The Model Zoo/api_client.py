import requests
import json
import time
import threading
import os

OPENROUTER_API_KEY = "OPENAPIKEY"  # Replace with your actual API key or set it as an environment variable

def call_openrouter(model_id, content):
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in environment variables")

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model_id,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.1,
                "session_id": "SK-session-1"
            }),
            timeout=130,
            
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] {model_id}: {e}")
        return None


def _call_async(model_id, prompt, result_container):
    result_container["response"] = call_openrouter(model_id, prompt)
    result_container["status"] = "success" if result_container["response"] else "error"


def call_with_heartbeat(model_id, prompt):
    result = {"status": "pending", "response": None}
    thread = threading.Thread(target=_call_async, args=(model_id, prompt, result))
    thread.start()

    start_time = time.time()
    last_heartbeat = start_time

    while thread.is_alive():
        elapsed = time.time() - start_time

        if elapsed > 120:
            print(f"[TIMEOUT] {model_id} exceeded 120s")
            return None, elapsed

        if time.time() - last_heartbeat >= 30:
            print(f"[HEARTBEAT] {model_id} running... ({int(elapsed)}s)")
            last_heartbeat = time.time()

        time.sleep(0.5)

    return result["response"], time.time() - start_time