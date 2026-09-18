from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Assertion:
    subject: str
    predicate: str
    object_text: str
    negated: bool
    agent_id: str
    hop_index: int
    ontology_code: Optional[str] = None
    ontology_name: Optional[str] = None
    ontology_source: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Assertion":
        return cls(**d)


@dataclass
class ContradictionResult:
    contradiction_type: str  # "B" or "C" for now (A/D once built)
    hop_a: int
    hop_b: int
    assertion_a: Assertion
    assertion_b: Assertion
    relation: str
    explanation: str

    def to_dict(self) -> dict:
        return {
            "contradiction_type": self.contradiction_type,
            "hop_a": self.hop_a,
            "hop_b": self.hop_b,
            "assertion_a": self.assertion_a.to_dict(),
            "assertion_b": self.assertion_b.to_dict(),
            "relation": self.relation,
            "explanation": self.explanation,
        }