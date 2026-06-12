"""Small offline LLM mock for the container example."""
import time


def ask(question: str) -> str:
    time.sleep(0.05)
    return f"Mock agent received: {question}"
