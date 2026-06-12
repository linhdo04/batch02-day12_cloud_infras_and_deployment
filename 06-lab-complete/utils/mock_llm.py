"""Offline LLM substitute used by the deployment lab."""
import random
import time


RESPONSES = [
    "The production agent received your question and is operating normally.",
    "This is an offline mock response. Replace this function with an LLM provider in production.",
    "Your request was processed successfully by the deployed AI agent.",
]


def ask(question: str, delay: float = 0.02) -> str:
    time.sleep(delay)
    lowered = question.lower()
    if "docker" in lowered:
        return "Docker packages the application and its dependencies into a portable container."
    if "deploy" in lowered:
        return "Deployment makes the agent available on a managed server through a public endpoint."
    return random.choice(RESPONSES)
