"""Graded decisions on top of confidence.

A confidence score is only useful if it changes what happens next. A
pass/fail gate throws that away: 250 and 130 both "pass" a floor of 128,
and a 40 looks the same as a 0 once it is refused. This module keeps the
gradient. Every value maps to one of four bands, and each band says what
the value is allowed to do:

    act        may drive an action on its own
    review     may drive an action only after a person signs off
    hold       may be shown, never acted on; the reason is given
    cant_tell  may be shown only as "can't tell"; the reason is given

Every decision also names the reason that limited it most (the weakest
input), lists the phrases or facts that drove the score, and records the
thresholds used, so the decision can be audited and replayed.

Nothing here is random and nothing reads the clock, so the same inputs
always give the same decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence, Tuple, Union

from . import C, CERTAIN, UNKNOWN

BANDS: Tuple[str, ...] = ("act", "review", "hold", "cant_tell")

# Why a score is low. A reason should name one of these, so audits can
# count causes across many decisions instead of parsing sentences.
REASON_CODES = (
    "missing_input",          # something needed was not provided
    "conflicting_sources",    # two inputs disagree
    "below_threshold",        # a component fell under its own floor
    "timeout",                # a source did not answer in time
    "out_of_range",           # a value is outside what the model covers
    "unverified_source",      # the source was not checked
    "weak_evidence",          # the text only hints at the claim
    "strong_evidence",        # the text states the claim directly
)

# Lowest score for each band, per profile. A score below the "hold" line
# is "cant_tell". Strict profiles have no review band: the act line and
# the review line are the same, so every non-act value stops.
PROFILES = {
    # everyday reading of tone, motive, or risk: a person sees the
    # answer, and a reviewer can approve action on mid-confidence reads
    "general": {"act": 224, "review": 160, "hold": 96},
    # clinical coding: a code suggestion below 'act' goes to a coder's
    # queue, never onto a claim
    "clinical_coding": {"act": 224, "review": 192, "hold": 128},
    # exchanges and financial institutions: act only when very sure;
    # everything else stops, with the explanation attached
    "financial_strict": {"act": 240, "review": 240, "hold": 128},
}

# Plain-words labels for people who will never read a number. Mirrors the
# bands so the words a user sees and the action the system takes agree.
LABELS = (
    (224, "very sure"),
    (160, "pretty sure"),
    (96, "not sure"),
    (0, "can't tell"),
)


def plain_label(score: int) -> str:
    """Map a 0-256 score to a plain phrase. Unknown is always "can't tell"."""
    s = _clamp(score)
    for floor, words in LABELS:
        if s >= floor:
            return words
    return "can't tell"  # pragma: no cover - LABELS ends at 0


def percent(score: int) -> int:
    """The score as a whole percent, 0-100, rounded half up."""
    s = _clamp(score)
    return (s * 100 + CERTAIN // 2) // CERTAIN


def _clamp(score: int) -> int:
    return max(0, min(CERTAIN, int(score)))


@dataclass(frozen=True)
class Reason:
    """One fact that moved a score. `code` should come from REASON_CODES,
    `text` is the sentence a person reads, and `evidence` holds the exact
    words or phrases from the source that drove the score."""

    code: str
    text: str
    score: int
    evidence: Tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "text": self.text,
            "score": _clamp(self.score),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class Decision:
    value: Any
    score: int
    band: str
    profile: str
    thresholds: dict
    limiting: Optional[Reason]
    reasons: Tuple[Reason, ...] = field(default_factory=tuple)

    @property
    def may_act(self) -> bool:
        return self.band == "act"

    @property
    def may_display(self) -> bool:
        # Every decision can be shown. Showing an unknown is the point.
        return True

    @property
    def label(self) -> str:
        return plain_label(self.score)

    def explain(self) -> str:
        """Plain-English account of the decision, suitable for a screen."""
        t = self.thresholds
        s = self.score
        reading = f"The reading is '{self.label}' ({percent(s)}%)"
        if self.band == "act":
            head = (f"Acting on this is allowed. {reading}, score {s} "
                    f"meets the act line of {t['act']}.")
        elif self.band == "review":
            head = (f"Needs a person to approve before acting. {reading}, "
                    f"score {s}: at or above the review line of "
                    f"{t['review']}, below the act line of {t['act']}.")
        elif self.band == "hold":
            if t["review"] == t["act"]:
                needs = f"{t['act']} to act; this profile has no review step"
            else:
                needs = f"{t['review']} for review, {t['act']} to act"
            head = (f"Shown only, not acted on. {reading}, but score {s} is "
                    f"below the line for action this profile needs "
                    f"({needs}).")
        elif self.value is None and self.score == 0:
            head = "Can't tell. The value is unknown, so it is shown only as unknown."
        else:
            head = (f"Can't tell. Score {s} is below the hold line of "
                    f"{t['hold']}, so it is shown only as unknown.")
        lines = [head]
        if self.limiting is not None:
            lines.append(f"Held back most by: {self.limiting.text}")
        for r in self.reasons:
            if r is self.limiting:
                continue
            lines.append(f"- {r.text}")
        return "\n".join(lines)

    def as_json(self) -> dict:
        """The one JSON shape every app result uses (see docs/decision-spec.md)."""
        return {
            "value": None if self.value is UNKNOWN or self.value is None else self.value,
            "score": _clamp(self.score),
            "percent": percent(self.score),
            "label": self.label,
            "band": self.band,
            "may_act": self.may_act,
            "may_display": self.may_display,
            "profile": self.profile,
            "thresholds": dict(self.thresholds),
            "limiting": self.limiting.as_dict() if self.limiting else None,
            "reasons": [r.as_dict() for r in self.reasons],
        }


def band_for(score: int, profile: str = "general") -> str:
    """Which band a score lands in under a profile."""
    t = _thresholds(profile)
    s = _clamp(score)
    if s >= t["act"]:
        return "act"
    if s >= t["review"]:
        return "review"
    if s >= t["hold"]:
        return "hold"
    return "cant_tell"


def decide(value: Union[C, Any],
           reasons: Iterable[Reason] = (),
           profile: str = "general") -> Decision:
    """Turn a confidence value and its reasons into a graded decision.

    The score is the value's own confidence. If the value is UNKNOWN the
    score is 0 and the band is "cant_tell", whatever the reasons say. The
    limiting reason is the one with the lowest score; ties go to the
    earliest reason, so the answer does not depend on set ordering.
    """
    t = _thresholds(profile)
    if isinstance(value, C):
        score = value.confidence
        raw = None if value.is_unknown else value.value
    elif value is UNKNOWN:
        score, raw = 0, None
    else:
        # A bare value was not confidence-tracked. Treat it as certain
        # only if the caller says so, by wrapping it in C(...). Otherwise
        # refuse to invent a score.
        raise TypeError(
            "decide() needs a C value (or UNKNOWN); wrap a plain value in "
            "C(value, confidence=...) with the confidence you can defend")
    if raw is None:
        score = 0
    reasons = tuple(reasons)
    limiting = None
    if reasons:
        limiting = min(reasons, key=lambda r: _clamp(r.score))
    band = band_for(score, profile)
    return Decision(value=raw, score=_clamp(score), band=band, profile=profile,
                    thresholds=t, limiting=limiting, reasons=reasons)


def require_band(decision: Decision, needed: str = "act") -> Any:
    """Return the value only if the decision is at least `needed`.

    Order: act > review > hold > cant_tell. Asking for "review" accepts
    "act" and "review". Anything lower raises ValueError with the
    decision's explanation, so the caller can show it instead of a bare
    failure.
    """
    order = {"act": 3, "review": 2, "hold": 1, "cant_tell": 0}
    if needed not in order:
        raise ValueError(f"unknown band {needed!r}")
    if order[decision.band] < order[needed]:
        raise ValueError(decision.explain())
    return decision.value


# ── audit ─────────────────────────────────────────────────────────────

def audit_record(decision: Decision, inputs: Sequence[Any],
                 outcome: str) -> dict:
    """One audit entry: inputs, score, threshold, outcome. No clock, no id
    generator, so replaying the same inputs reproduces the same record."""
    return {
        "inputs": [_jsonable(x) for x in inputs],
        "score": decision.score,
        "band": decision.band,
        "profile": decision.profile,
        "threshold": dict(decision.thresholds),
        "outcome": outcome,
    }


def append_audit(path: str, record: dict) -> None:
    """Append one record as a JSON line. The file is opened in append mode
    and never rewritten, so earlier entries cannot be changed by this API."""
    line = json.dumps(record, sort_keys=True, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ── helpers ───────────────────────────────────────────────────────────

def _thresholds(profile: str) -> dict:
    if profile not in PROFILES:
        raise ValueError(
            f"unknown profile {profile!r}; choose one of {sorted(PROFILES)}")
    return dict(PROFILES[profile])


def _jsonable(x: Any) -> Any:
    if isinstance(x, C):
        return {"value": None if x.is_unknown else x.value,
                "confidence": x.confidence}
    if x is UNKNOWN:
        return {"value": None, "confidence": 0}
    return x
