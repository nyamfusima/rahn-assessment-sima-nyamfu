"""Shared pytest fixtures. Tests run with no API key and with network access blocked (AC-07)."""

import json
import socket
from typing import Optional

import pytest

from fitdesk.knowledge_base import KnowledgeBase


@pytest.fixture(autouse=True)
def no_api_key_and_no_network(monkeypatch):
    for name in ("GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def kb() -> KnowledgeBase:
    return KnowledgeBase.load()  # the real approved data file


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "status_log.json"


def read_log(path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


class FakeClassifier:
    """Stands in for GeminiClassifier: returns canned text or raises a canned error."""

    def __init__(self, response: Optional[str] = None, error: Optional[Exception] = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[str] = []

    def classify(self, message: str) -> Optional[str]:
        self.calls.append(message)
        if self.error is not None:
            raise self.error
        return self.response


class ScriptedInput:
    """Feeds pre-set answers to input(); fails the test if asked more times than expected."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise AssertionError(f"Unexpected prompt: {prompt!r}")
        return self.answers.pop(0)


def ai_json(intent="pricing", packages=(), asks_saturday=False, times=(), unsupported=(), approval=True) -> str:
    return json.dumps(
        {
            "intent": intent,
            "details": {
                "packages": list(packages),
                "asks_saturday_availability": asks_saturday,
                "saturday_times": list(times),
                "unsupported_requests": list(unsupported),
            },
            "requires_human_approval": approval,
        }
    )
