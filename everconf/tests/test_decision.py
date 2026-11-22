"""Tests for graded decisions. Each claim in docs/decision-spec.md is
checked here: band edges, the limiting reason, determinism, the JSON
shape, and the append-only audit log."""

import json

import pytest

from everconf import (C, UNKNOWN, Reason, append_audit, audit_record,
                      band_for, decide, plain_label, percent, require_band)


# ── bands ──

@pytest.mark.parametrize("score,band", [
    (256, "act"), (224, "act"), (223, "review"), (192, "review"),
    (191, "hold"), (128, "hold"), (127, "cant_tell"), (0, "cant_tell"),
])
def test_clinical_coding_band_edges(score, band):
    assert band_for(score, "clinical_coding") == band


def test_general_band_edges():
    assert band_for(224, "general") == "act"
    assert band_for(160, "general") == "review"
    assert band_for(96, "general") == "hold"
    assert band_for(95, "general") == "cant_tell"


def test_financial_strict_has_no_review_band():
    # Strict: act at 240 and up. Everything below is a stop, never review.
    assert band_for(240, "financial_strict") == "act"
    assert band_for(239, "financial_strict") == "hold"
    assert band_for(200, "financial_strict") == "hold"
    assert band_for(127, "financial_strict") == "cant_tell"
    for s in range(0, 257):
        assert band_for(s, "financial_strict") != "review"


def test_unknown_profile_is_refused():
    with pytest.raises(ValueError):
        band_for(200, "casual")


def test_graded_not_binary():
    # The point of the module: 250 and 130 are different decisions,
    # not both "pass".
    assert band_for(250, "general") == "act"
    assert band_for(130, "general") == "hold"
    assert band_for(40, "general") == "cant_tell"


# ── decide() ──

def test_unknown_is_cant_tell_whatever_the_reasons():
    d = decide(UNKNOWN, [Reason("missing_input", "label absent", 0)])
    assert d.band == "cant_tell"
    assert d.score == 0
    assert d.value is None
    assert d.may_act is False
    assert d.may_display is True


def test_bare_value_is_refused():
    with pytest.raises(TypeError):
        decide(0.9)


def test_limiting_reason_is_lowest_score():
    reasons = [
        Reason("strong_evidence", "states the amount", 250),
        Reason("unverified_source", "payee not checked", 120),
        Reason("weak_evidence", "tone is inferred", 200),
    ]
    d = decide(C("pay", confidence=120), reasons, "general")
    assert d.limiting is reasons[1]
    assert d.band == "hold"


def test_limiting_reason_tie_goes_to_earliest():
    a = Reason("conflicting_sources", "first", 100)
    b = Reason("timeout", "second", 100)
    assert decide(C(1, confidence=100), [a, b]).limiting is a
    assert decide(C(1, confidence=100), [b, a]).limiting is b


def test_decision_is_deterministic():
    reasons = [Reason("weak_evidence", "x", 180, ("maybe",)),
               Reason("strong_evidence", "y", 230, ("will pay",))]
    first = decide(C(7, confidence=180), reasons, "clinical_coding").as_json()
    for _ in range(50):
        again = decide(C(7, confidence=180), reasons,
                       "clinical_coding").as_json()
        assert again == first


def test_require_band_accepts_and_refuses():
    d = decide(C(5, confidence=200), [], "general")   # review band
    assert require_band(d, "review") == 5
    assert require_band(d, "hold") == 5
    with pytest.raises(ValueError) as exc:
        require_band(d, "act")
    assert "Needs a person to approve" in str(exc.value)


def test_require_band_unknown_name():
    with pytest.raises(ValueError):
        require_band(decide(C(1, confidence=256)), "maybe")


def test_explain_names_the_limit():
    d = decide(C("claim", confidence=150),
               [Reason("unverified_source", "the payer was not checked", 150)],
               "clinical_coding")
    text = d.explain()
    assert "Shown only" in text
    assert "the payer was not checked" in text


# ── plain words and percent ──

@pytest.mark.parametrize("score,words", [
    (256, "very sure"), (224, "very sure"), (200, "pretty sure"),
    (160, "pretty sure"), (120, "not sure"), (96, "not sure"),
    (95, "can't tell"), (0, "can't tell"),
])
def test_plain_labels(score, words):
    assert plain_label(score) == words


def test_percent_rounds_half_up():
    assert percent(0) == 0
    assert percent(128) == 50
    assert percent(256) == 100
    assert percent(1) == 0      # 0.39% rounds down
    assert percent(2) == 1      # 0.78% rounds up


# ── JSON shape ──

def test_as_json_shape():
    reasons = [Reason("weak_evidence", "tone inferred", 170, ("feels like",))]
    j = decide(C("hostile", confidence=170), reasons, "general").as_json()
    assert set(j) == {"value", "score", "percent", "label", "band",
                      "may_act", "may_display", "profile", "thresholds",
                      "limiting", "reasons"}
    assert j["value"] == "hostile"
    assert j["score"] == 170
    assert j["percent"] == 66
    assert j["label"] == "pretty sure"
    assert j["band"] == "review"
    assert j["reasons"][0]["evidence"] == ["feels like"]
    assert j["limiting"]["code"] == "weak_evidence"
    json.dumps(j)   # must be serialisable as-is


def test_as_json_unknown_has_null_value():
    j = decide(UNKNOWN).as_json()
    assert j["value"] is None
    assert j["score"] == 0
    assert j["label"] == "can't tell"


# ── audit ──

def test_audit_record_fields(tmp_path):
    d = decide(C(9, confidence=130), [], "financial_strict")
    rec = audit_record(d, [C(9, confidence=130), UNKNOWN], outcome="held")
    assert rec["inputs"] == [{"value": 9, "confidence": 130},
                             {"value": None, "confidence": 0}]
    assert rec["score"] == 130
    assert rec["band"] == "hold"
    assert rec["threshold"] == {"act": 240, "review": 240, "hold": 128}
    assert rec["outcome"] == "held"


def test_audit_is_append_only(tmp_path):
    path = tmp_path / "audit.jsonl"
    d = decide(C(1, confidence=256), [], "financial_strict")
    r1 = audit_record(d, [C(1)], "settled")
    r2 = audit_record(d, [C(1)], "refused")
    append_audit(str(path), r1)
    first_bytes = path.read_bytes()
    append_audit(str(path), r2)
    assert path.read_bytes().startswith(first_bytes)
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["outcome"] == "settled"
    assert json.loads(lines[1])["outcome"] == "refused"


def test_audit_lines_are_stable(tmp_path):
    # Same record written twice gives identical bytes (sorted keys, no clock).
    d = decide(C(3, confidence=200), [], "general")
    rec = audit_record(d, [C(3, confidence=200)], "shown")
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    append_audit(str(a), rec)
    append_audit(str(b), rec)
    assert a.read_bytes() == b.read_bytes()


def test_explain_states_the_threshold_it_missed():
    # The wording must agree with the band: a "very sure" reading that is
    # still held back has to say which line it fell short of.
    d = decide(C("settle", confidence=236),
               [Reason("unverified_source", "one feed only", 236)],
               "financial_strict")
    text = d.explain()
    assert "very sure" in text
    assert "score 236" in text
    assert "240 to act" in text
    assert "Shown only" in text
