"""Builds the draft reply from approved facts only, or the exact escalation phrase.

Safety rule (FR-04, Playbook Rule 1): every fact in the draft comes from a KnowledgeBase
object (package name, price, slot time, slot status). No text produced by the AI is ever
copied into the draft. The AI's labels are only used as lookup keys.
"""

from dataclasses import dataclass

from fitdesk.knowledge_base import KnowledgeBase, Package, SaturdaySlot
from fitdesk.models import AIEnquiry

ESCALATION_PHRASE = "I'll check with the owner and come back to you."


@dataclass(frozen=True)
class Draft:
    text: str
    is_escalation: bool


def format_price(price_zar: int) -> str:
    """180 -> 'R180', 1680 -> 'R1,680'."""
    return f"R{price_zar:,}"


def _package_sentence(package: Package) -> str:
    return f"The {package.name} package costs {format_price(package.price_zar)}."


def _all_packages_sentence(packages: list[Package]) -> str:
    parts = [f"{p.name} {format_price(p.price_zar)}" for p in packages]
    return "Our packages are: " + ", ".join(parts) + "."


def _slot_sentence(slot: SaturdaySlot) -> str:
    return f"Saturday {slot.time} is {slot.status}."


def _all_slots_sentence(slots: list[SaturdaySlot]) -> str:
    available = [s.time for s in slots if s.status == "available"]
    full = [s.time for s in slots if s.status == "full"]
    parts = []
    if available:
        parts.append("available: " + ", ".join(available))
    if full:
        parts.append("full: " + ", ".join(full))
    return "Saturday slots " + "; ".join(parts) + "."


def build_draft(enquiry: AIEnquiry, kb: KnowledgeBase) -> Draft:
    """Return a draft built only from the data file.

    If any part of the enquiry cannot be answered from the data, the exact escalation
    phrase is added and the draft is marked as an escalation (SRS Q1). If nothing can be
    answered, the draft is exactly the escalation phrase (AC-02).
    """
    details = enquiry.details
    sentences: list[str] = []
    missing = False

    asks_prices = enquiry.intent in ("pricing", "pricing_and_availability")
    asks_saturday = details.asks_saturday_availability or enquiry.intent in (
        "saturday_availability",
        "pricing_and_availability",
    )

    # Prices
    if details.packages:
        for label in details.packages:
            package = kb.find_package(label)
            if package is None:
                missing = True
            else:
                sentence = _package_sentence(package)
                if sentence not in sentences:
                    sentences.append(sentence)
    elif asks_prices:
        if kb.packages:
            sentences.append(_all_packages_sentence(kb.packages))
        else:
            missing = True

    # Saturday availability
    if details.saturday_times:
        for label in details.saturday_times:
            slot = kb.find_saturday_slot(label)
            if slot is None:
                missing = True
            else:
                sentence = _slot_sentence(slot)
                if sentence not in sentences:
                    sentences.append(sentence)
    elif asks_saturday:
        if kb.saturday_slots:
            sentences.append(_all_slots_sentence(kb.saturday_slots))
        else:
            missing = True

    # Anything else the customer asked for is not in the data.
    if details.unsupported_requests:
        missing = True

    # Nothing answerable was identified (e.g. intent "other").
    if not sentences:
        missing = True

    if missing:
        sentences.append(ESCALATION_PHRASE)
    return Draft(text=" ".join(sentences), is_escalation=missing)
