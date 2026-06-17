"""
eligibility/models.py
---------------------
Dataclasses for eligibility engine inputs and outputs.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class CriterionResult:
    criterion_id: str
    passed: bool
    reason: str
    actual_value: Any = None


@dataclass
class MatchResult:
    patient_id: str
    trial_id: str
    nct_id: str
    trial_title: str
    primary_indication: str
    phase: str
    matched_criteria: list[CriterionResult] = field(default_factory=list)
    disqualifiers: list[CriterionResult]    = field(default_factory=list)
    evaluated_at: datetime                  = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_inclusion_criteria(self) -> int:
        return len(self.matched_criteria) + len(self.disqualifiers)

    @property
    def match_score(self) -> float:
        if self.total_inclusion_criteria == 0:
            return 0.0
        return round(len(self.matched_criteria) / self.total_inclusion_criteria, 4)

    @property
    def is_fully_eligible(self) -> bool:
        return len(self.disqualifiers) == 0 and len(self.matched_criteria) > 0