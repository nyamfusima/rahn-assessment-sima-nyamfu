"""Loads and queries the approved data file; the only source of facts."""

import json
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ValidationError

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "fitdesk_data.json"

_PACKAGE_FILLER_WORDS = {"pack", "packs", "package", "packages", "bundle", "the", "a", "an", "of"}


class KnowledgeBaseError(Exception):
    """The data file is missing, unreadable or not in the expected shape."""


class Package(BaseModel):
    id: str
    name: str
    price_zar: int


class SaturdaySlot(BaseModel):
    time: str
    status: Literal["available", "full"]


class FitDeskData(BaseModel):
    packages: list[Package]
    saturday_availability: list[SaturdaySlot]


def _canonical_package_text(text: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    tokens = [t for t in tokens if t not in _PACKAGE_FILLER_WORDS]
    tokens = ["session" if t == "sessions" else t for t in tokens]
    return " ".join(tokens)


def normalise_time(text: str) -> Optional[str]:
    """Turn '9:00', '09:00' or '0900' into 'HH:MM'. Returns None if it is not a clock time."""
    match = re.fullmatch(r"\s*(\d{1,2})[:h.]?(\d{2})\s*", text)
    if not match:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours > 23 or minutes > 59:
        return None
    return f"{hours:02d}:{minutes:02d}"


class KnowledgeBase:
    def __init__(self, data: FitDeskData) -> None:
        self._data = data

    @classmethod
    def load(cls, path: Path = DEFAULT_DATA_PATH) -> "KnowledgeBase":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls(FitDeskData.model_validate(raw))
        except OSError as exc:
            raise KnowledgeBaseError(f"Cannot read data file {path}: {exc}") from exc
        except (json.JSONDecodeError, ValidationError) as exc:
            raise KnowledgeBaseError(f"Data file {path} is not in the expected format") from exc

    @property
    def packages(self) -> list[Package]:
        return list(self._data.packages)

    @property
    def saturday_slots(self) -> list[SaturdaySlot]:
        return list(self._data.saturday_availability)

    def find_package(self, query: str) -> Optional[Package]:
        wanted = _canonical_package_text(query)
        if not wanted:
            return None
        for package in self._data.packages:
            if _canonical_package_text(package.name) == wanted:
                return package
        return None

    def find_saturday_slot(self, query: str) -> Optional[SaturdaySlot]:
        wanted = normalise_time(query)
        if wanted is None:
            return None
        for slot in self._data.saturday_availability:
            if slot.time == wanted:
                return slot
        return None
