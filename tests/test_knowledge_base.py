"""Knowledge base and draft-building tests (FR-03, FR-04, AC-01, AC-02)."""

import re

import pytest

from fitdesk.knowledge_base import KnowledgeBase, KnowledgeBaseError, normalise_time
from fitdesk.models import parse_ai_response
from fitdesk.response_builder import ESCALATION_PHRASE, build_draft
from tests.conftest import ai_json

PRICE_PATTERN = re.compile(r"R\d{1,3}(?:,\d{3})*")  # R180, R1,680 (a trailing list comma is not part of it)


def test_data_file_has_exactly_the_approved_facts(kb):
    assert [(p.name, p.price_zar) for p in kb.packages] == [
        ("Single session", 180),
        ("5 sessions", 800),
        ("12 sessions", 1680),
    ]
    assert [(s.time, s.status) for s in kb.saturday_slots] == [
        ("09:00", "available"),
        ("10:00", "full"),
        ("11:00", "available"),
    ]


@pytest.mark.parametrize(
    "label, expected_id",
    [
        ("12 sessions", "12_sessions"),
        ("12-session pack", "12_sessions"),
        ("the 5 session package", "5_sessions"),
        ("Single session", "single_session"),
        ("20 sessions", None),
        ("", None),
    ],
)
def test_find_package(kb, label, expected_id):
    package = kb.find_package(label)
    assert (package.id if package else None) == expected_id


@pytest.mark.parametrize("text, expected", [("9:00", "09:00"), ("0900", "09:00"), ("14:00", "14:00"), ("9am", None), ("25:00", None)])
def test_normalise_time(text, expected):
    assert normalise_time(text) == expected


def test_missing_data_file_raises_clear_error(tmp_path):
    with pytest.raises(KnowledgeBaseError):
        KnowledgeBase.load(tmp_path / "missing.json")


def test_malformed_data_file_raises_clear_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"packages": "oops"}', encoding="utf-8")
    with pytest.raises(KnowledgeBaseError):
        KnowledgeBase.load(bad)


# --- Draft building ------------------------------------------------------------------------


def draft_for(kb, **kwargs):
    return build_draft(parse_ai_response(ai_json(**kwargs)), kb)


def test_ac01_twelve_session_price_only(kb):
    draft = draft_for(kb, intent="pricing", packages=["12 sessions"])
    assert "R1,680" in draft.text
    assert PRICE_PATTERN.findall(draft.text) == ["R1,680"]
    assert not draft.is_escalation


def test_ac02_unknown_package_is_exact_escalation(kb):
    draft = draft_for(kb, intent="pricing", packages=["20 sessions"])
    assert draft.text == ESCALATION_PHRASE
    assert draft.is_escalation


def test_ac02_unknown_saturday_time_is_exact_escalation(kb):
    draft = draft_for(kb, intent="saturday_availability", asks_saturday=True, times=["14:00"])
    assert draft.text == ESCALATION_PHRASE
    assert "available" not in draft.text and "full" not in draft.text


def test_other_intent_is_exact_escalation(kb):
    draft = draft_for(kb, intent="other", unsupported=["parking"])
    assert draft.text == ESCALATION_PHRASE


def test_specific_saturday_slots_from_data(kb):
    draft = draft_for(kb, intent="saturday_availability", asks_saturday=True, times=["9:00", "10:00"])
    assert draft.text == "Saturday 09:00 is available. Saturday 10:00 is full."
    assert not draft.is_escalation


def test_brief_example_price_and_all_saturday_slots(kb):
    draft = draft_for(kb, intent="pricing_and_availability", packages=["12 sessions"], asks_saturday=True)
    assert draft.text == (
        "The 12 sessions package costs R1,680. "
        "Saturday slots available: 09:00, 11:00; full: 10:00."
    )


def test_general_price_question_lists_all_packages(kb):
    draft = draft_for(kb, intent="pricing")
    assert PRICE_PATTERN.findall(draft.text) == ["R180", "R800", "R1,680"]


def test_partly_answerable_enquiry_states_facts_then_escalates(kb):
    draft = draft_for(kb, intent="pricing", packages=["12 sessions"], unsupported=["Sunday slots"])
    assert draft.text == f"The 12 sessions package costs R1,680. {ESCALATION_PHRASE}"
    assert draft.is_escalation


def test_ai_labels_are_never_copied_into_the_draft(kb):
    # Even if the AI puts a made-up price into a label, only data-file facts appear.
    draft = draft_for(kb, intent="pricing", packages=["12 sessions for R99"])
    assert "R99" not in draft.text
    assert draft.text == ESCALATION_PHRASE
