import json
from models import Assertion


class AssertionStore:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.assertions: list[Assertion] = []

    def add(self, assertion: Assertion) -> None:
        self.assertions.append(assertion)

    def add_many(self, assertions: list[Assertion]) -> None:
        self.assertions.extend(assertions)

    def all(self) -> list[Assertion]:
        """Everything in hand-off order (the order they were added)."""
        return list(self.assertions)

    def before_hop(self, hop_index: int) -> list[Assertion]:
        return [a for a in self.assertions if a.hop_index < hop_index]

    def by_ontology_code(self, code: str) -> list[Assertion]:
        return [a for a in self.assertions if a.ontology_code == code]

    def by_predicate(self, predicate: str) -> list[Assertion]:
        return [a for a in self.assertions if a.predicate == predicate]

    def to_json(self) -> str:
        return json.dumps({
            "session_id": self.session_id,
            "assertions": [a.to_dict() for a in self.assertions],
        }, indent=2)

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "AssertionStore":
        with open(path) as f:
            data = json.load(f)
        store = cls(data["session_id"])
        store.assertions = [Assertion.from_dict(a) for a in data["assertions"]]
        return store

    def __repr__(self) -> str:
        return f"AssertionStore(session={self.session_id}, n={len(self.assertions)})"


if __name__ == "__main__":
    store = AssertionStore(session_id="test_patient_001")

    store.add(Assertion(
        subject="patient", predicate="no_known_allergy", object_text="known allergies",
        negated=True, agent_id="triage_agent", hop_index=1,
        ontology_code="C0013182", ontology_name="Drug Allergy", ontology_source="MTH",
    ))
    store.add(Assertion(
        subject="patient", predicate="has_condition", object_text="type 2 diabetes mellitus",
        negated=False, agent_id="triage_agent", hop_index=1,
        ontology_code="C0011860", ontology_name="Diabetes Mellitus, Non-Insulin-Dependent",
        ontology_source="MTH",
    ))
    store.add(Assertion(
        subject="patient", predicate="takes_medication", object_text="metformin",
        negated=False, agent_id="diagnostic_agent", hop_index=2,
        ontology_code="C0025598", ontology_name="metformin", ontology_source="MTH",
    ))

    print(store)
    print("\nAll assertions:")
    for a in store.all():
        print(f"  hop {a.hop_index} [{a.agent_id}] {a.predicate} -> {a.object_text} (negated={a.negated})")

    print("\nAssertions visible before hop 2 (what a hop-2 agent's claim would be checked against):")
    for a in store.before_hop(2):
        print(f"  {a.object_text}")

    print("\nRound-trip save/load test:")
    store.save("test_session.json")
    reloaded = AssertionStore.load("test_session.json")
    print(f"  Reloaded: {reloaded}, matches original count: {len(reloaded.all()) == len(store.all())}")