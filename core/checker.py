from models import Assertion, ContradictionResult
from assertion_store import AssertionStore
from umls_client import get_relation_targets, get_relations, get_parents

MEDICATION_PREDICATES = {"takes_medication", "recommends_medication", "recommends_treatment"}
CONDITION_PREDICATES = {"has_condition"}
PINNED_SIBLING_PARENTS = []


def check_type_b(new_assertion: Assertion, store: AssertionStore) -> list[ContradictionResult]:
    results = []
    if new_assertion.predicate not in MEDICATION_PREDICATES or new_assertion.negated:
        return results

    prior_conditions = [
        a for a in store.before_hop(new_assertion.hop_index)
        if a.predicate in CONDITION_PREDICATES and not a.negated and a.ontology_code
    ]

    for condition in prior_conditions:
        contraindicated = get_relation_targets(
            condition.ontology_code, sabs="MED-RT", additional_label="has_contraindicated_drug"
        )
        contraindicated_names = [t["target_name"].lower() for t in contraindicated if t["target_name"] != "?"]

        drug_name = (new_assertion.ontology_name or new_assertion.object_text).lower()
        object_text_lower = new_assertion.object_text.lower()
        match = any(
            name in drug_name or drug_name in name
            or name in object_text_lower or object_text_lower in name
            for name in contraindicated_names
        )
        if match:
            results.append(ContradictionResult(
                contradiction_type="B",
                hop_a=condition.hop_index,
                hop_b=new_assertion.hop_index,
                assertion_a=condition,
                assertion_b=new_assertion,
                relation="has_contraindicated_drug",
                explanation=(
                    f"Hop {new_assertion.hop_index} ({new_assertion.agent_id}) recommends/asserts "
                    f"'{new_assertion.object_text}', which is contraindicated for "
                    f"'{condition.object_text}' — established at hop {condition.hop_index} "
                    f"by {condition.agent_id}."
                ),
            ))
    return results


def check_type_c(new_assertion: Assertion, store: AssertionStore) -> list[ContradictionResult]:
    results = []
    if new_assertion.predicate not in CONDITION_PREDICATES or new_assertion.negated:
        return results

    prior_negated = [
        a for a in store.before_hop(new_assertion.hop_index)
        if a.ontology_code and (
            (a.predicate in CONDITION_PREDICATES and a.negated)
            or a.predicate == "excludes_condition"
        )
    ]
    if not prior_negated:
        return results

    candidate_name = (new_assertion.ontology_name or new_assertion.object_text).lower()
    object_text_lower = new_assertion.object_text.lower()

    for prior in prior_negated:
        children = get_relation_targets(prior.ontology_code, sabs="SNOMEDCT_US", additional_label="isa")
        child_names = [c["target_name"].lower() for c in children if c["target_name"] != "?"]
        match = any(
            name in candidate_name or candidate_name in name
            or name in object_text_lower or object_text_lower in name
            for name in child_names
        )
        if match:
            results.append(ContradictionResult(
                contradiction_type="C",
                hop_a=prior.hop_index,
                hop_b=new_assertion.hop_index,
                assertion_a=prior,
                assertion_b=new_assertion,
                relation="isa",
                explanation=(
                    f"Hop {new_assertion.hop_index} ({new_assertion.agent_id}) asserts "
                    f"'{new_assertion.object_text}', which is a subtype of "
                    f"'{prior.object_text}' — but hop {prior.hop_index} ({prior.agent_id}) "
                    f"explicitly excluded '{prior.object_text}'."
                ),
            ))
    return results


DISCONTINUATION_PREDICATES = {"discontinued_medication"}
ACTIVE_MEDICATION_PREDICATES = {"takes_medication", "recommends_medication", "recommends_treatment"}


def _resolve_status(assertion: Assertion) -> tuple[str, str] | None:
    if assertion.predicate in ACTIVE_MEDICATION_PREDICATES and not assertion.negated:
        return ("medication", "active")
    if assertion.predicate in DISCONTINUATION_PREDICATES:
        return ("medication", "discontinued")
    if assertion.predicate == "has_condition" and not assertion.negated:
        return ("condition", "present")
    if assertion.predicate == "has_condition" and assertion.negated:
        return ("condition", "ruled_out")
    if assertion.predicate == "excludes_condition":
        return ("condition", "ruled_out")
    return None


SUPERSEDED_STATUS = {"discontinued", "ruled_out"}


def check_type_d(new_assertion: Assertion, store: AssertionStore) -> list[ContradictionResult]:
    results = []
    new_status = _resolve_status(new_assertion)
    if new_status is None:
        return results
    entity_type, status = new_status
    if status in SUPERSEDED_STATUS:
        return results  # only check assertions claiming an ACTIVE/PRESENT status

    def same_object(a: Assertion) -> bool:
        if new_assertion.ontology_code and a.ontology_code:
            if a.ontology_code == new_assertion.ontology_code:
                return True
        return (
            a.object_text.lower() in new_assertion.object_text.lower()
            or new_assertion.object_text.lower() in a.object_text.lower()
        )

    timeline = []
    for a in store.before_hop(new_assertion.hop_index):
        a_status = _resolve_status(a)
        if a_status is not None and a_status[0] == entity_type and same_object(a):
            timeline.append((a, a_status[1]))

    if not timeline:
        return results

    most_recent_assertion, most_recent_status = sorted(timeline, key=lambda pair: pair[0].hop_index)[-1]
    if most_recent_status in SUPERSEDED_STATUS:
        results.append(ContradictionResult(
            contradiction_type="D",
            hop_a=most_recent_assertion.hop_index,
            hop_b=new_assertion.hop_index,
            assertion_a=most_recent_assertion,
            assertion_b=new_assertion,
            relation=f"stale_status_after_{most_recent_status}",
            explanation=(
                f"Hop {new_assertion.hop_index} ({new_assertion.agent_id}) asserts "
                f"'{new_assertion.object_text}' as {status}, but hop "
                f"{most_recent_assertion.hop_index} ({most_recent_assertion.agent_id}) "
                f"already recorded it as {most_recent_status} — this claim relies on a "
                f"status that has since been superseded."
            ),
        ))
    return results


def check_type_a(new_assertion: Assertion, store: AssertionStore) -> list[ContradictionResult]:
    results = []
    if new_assertion.predicate not in CONDITION_PREDICATES or new_assertion.negated:
        return results
    if not new_assertion.ontology_name:
        return results

    prior_positive = [
        a for a in store.before_hop(new_assertion.hop_index)
        if a.predicate in CONDITION_PREDICATES and not a.negated
        and a.ontology_code and a.ontology_code != new_assertion.ontology_code
        and a.ontology_name
    ]
    if not prior_positive:
        return results

    for parent_cui in PINNED_SIBLING_PARENTS:
        children = get_relation_targets(parent_cui, sabs="SNOMEDCT_US", additional_label="isa")
        child_names = {c["target_name"].lower() for c in children if c["target_name"] != "?"}
        if not child_names:
            continue

        new_is_sibling = new_assertion.ontology_name.lower() in child_names
        if not new_is_sibling:
            continue

        for prior in prior_positive:
            if prior.ontology_name.lower() in child_names:
                results.append(ContradictionResult(
                    contradiction_type="A",
                    hop_a=prior.hop_index,
                    hop_b=new_assertion.hop_index,
                    assertion_a=prior,
                    assertion_b=new_assertion,
                    relation=f"sibling_under_pinned_parent:{parent_cui}",
                    explanation=(
                        f"Hop {new_assertion.hop_index} ({new_assertion.agent_id}) asserts "
                        f"'{new_assertion.object_text}', which is a sibling classification of "
                        f"'{prior.object_text}' asserted at hop {prior.hop_index} "
                        f"({prior.agent_id}) — these are typically mutually exclusive "
                        f"primary classifications."
                    ),
                ))
    return results


def check_new_assertion(new_assertion: Assertion, store: AssertionStore) -> list[ContradictionResult]:
    """Run all available checks against one new assertion."""
    results = []
    results.extend(check_type_a(new_assertion, store))
    results.extend(check_type_b(new_assertion, store))
    results.extend(check_type_c(new_assertion, store))
    results.extend(check_type_d(new_assertion, store))
    return results


def verify_session(assertions_by_hop: list[list[Assertion]], session_id: str) -> tuple[AssertionStore, list[ContradictionResult]]:
    """
    Process a full session hop-by-hop: for each hop's assertions, check
    them against everything already in the store BEFORE adding them.
    Returns the final store and every contradiction found along the way.
    """
    store = AssertionStore(session_id=session_id)
    all_results = []

    for hop_assertions in assertions_by_hop:
        for assertion in hop_assertions:
            results = check_new_assertion(assertion, store)
            all_results.extend(results)
        store.add_many(hop_assertions)

    return store, all_results


if __name__ == "__main__":
    hop1_a = [Assertion(
        subject="patient", predicate="has_condition", object_text="Type 1 diabetes mellitus",
        negated=False, agent_id="triage_agent", hop_index=1,
        ontology_code="C0011854", ontology_name="Diabetes Mellitus, Insulin-Dependent", ontology_source="MTH",
    )]
    hop3_a = [Assertion(
        subject="patient", predicate="has_condition", object_text="Type 2 diabetes mellitus",
        negated=False, agent_id="diagnostic_agent", hop_index=3,
        ontology_code="C0011860", ontology_name="Diabetes Mellitus, Non-Insulin-Dependent", ontology_source="MTH",
    )]
    store_a, results_a = verify_session([hop1_a, hop3_a], session_id="manual_test_004_type_a")
    print(f"--- TYPE A case: {store_a} ---")
    print(f"Contradictions found: {len(results_a)} (expected: 1, IF the CUI is correct)")
    for r in results_a:
        print(f"\n  Type {r.contradiction_type} | hops {r.hop_a}->{r.hop_b} | relation: {r.relation}")
        print(f"  {r.explanation}")

    # Positive case: known contraindication (kidney disease + ergotamine)
    hop1 = [Assertion(
        subject="patient", predicate="has_condition", object_text="kidney disease",
        negated=False, agent_id="triage_agent", hop_index=1,
        ontology_code="C0022658", ontology_name="Kidney Diseases", ontology_source="MTH",
    )]
    hop2 = [Assertion(
        subject="patient", predicate="recommends_medication", object_text="ergotamine",
        negated=False, agent_id="treatment_agent", hop_index=2,
        ontology_code=None, ontology_name="ergotamine", ontology_source=None,
    )]

    store, results = verify_session([hop1, hop2], session_id="manual_test_001_positive")
    print(f"--- POSITIVE case: {store} ---")
    print(f"Contradictions found: {len(results)} (expected: 1)")
    for r in results:
        print(f"\n  Type {r.contradiction_type} | hops {r.hop_a}->{r.hop_b} | relation: {r.relation}")
        print(f"  {r.explanation}")
    hop2_safe = [Assertion(
        subject="patient", predicate="recommends_medication", object_text="acetaminophen",
        negated=False, agent_id="treatment_agent", hop_index=2,
        ontology_code=None, ontology_name="acetaminophen", ontology_source=None,
    )]

    store2, results2 = verify_session([hop1, hop2_safe], session_id="manual_test_002_negative")
    print(f"\n--- NEGATIVE case: {store2} ---")
    print(f"Contradictions found: {len(results2)} (expected: 0)")
    for r in results2:
        print(f"\n  UNEXPECTED Type {r.contradiction_type} | hops {r.hop_a}->{r.hop_b} | relation: {r.relation}")
        print(f"  {r.explanation}")
    hop1_d = [Assertion(
        subject="patient", predicate="takes_medication", object_text="metformin",
        negated=False, agent_id="triage_agent", hop_index=1,
        ontology_code="C0025598", ontology_name="metformin", ontology_source="MTH",
    )]
    hop2_d = [Assertion(
        subject="patient", predicate="discontinued_medication", object_text="metformin",
        negated=False, agent_id="diagnostic_agent", hop_index=2,
        ontology_code="C0025598", ontology_name="metformin", ontology_source="MTH",
    )]
    hop4_d = [Assertion(
        subject="patient", predicate="recommends_medication", object_text="metformin",
        negated=False, agent_id="treatment_agent", hop_index=4,
        ontology_code="C0025598", ontology_name="metformin", ontology_source="MTH",
    )]
    store_d, results_d = verify_session([hop1_d, hop2_d, hop4_d], session_id="manual_test_003_type_d")
    print(f"\n--- TYPE D (medication) case: {store_d} ---")
    print(f"Contradictions found: {len(results_d)} (expected: 1)")
    for r in results_d:
        print(f"\n  Type {r.contradiction_type} | hops {r.hop_a}->{r.hop_b} | relation: {r.relation}")
        print(f"  {r.explanation}")
    hop1_dc = [Assertion(
        subject="patient", predicate="has_condition", object_text="pneumonia",
        negated=False, agent_id="triage_agent", hop_index=1,
        ontology_code="C0032285", ontology_name="Pneumonia", ontology_source="MTH",
    )]
    hop2_dc = [Assertion(
        subject="patient", predicate="has_condition", object_text="pneumonia",
        negated=True, agent_id="diagnostic_agent", hop_index=2,
        ontology_code="C0032285", ontology_name="Pneumonia", ontology_source="MTH",
    )]
    hop4_dc = [Assertion(
        subject="patient", predicate="has_condition", object_text="pneumonia",
        negated=False, agent_id="treatment_agent", hop_index=4,
        ontology_code="C0032285", ontology_name="Pneumonia", ontology_source="MTH",
    )]
    store_dc, results_dc = verify_session([hop1_dc, hop2_dc, hop4_dc], session_id="manual_test_005_type_d_condition")
    print(f"\n--- TYPE D (condition) case: {store_dc} ---")
    print(f"Contradictions found: {len(results_dc)} (expected: 1)")
    for r in results_dc:
        print(f"\n  Type {r.contradiction_type} | hops {r.hop_a}->{r.hop_b} | relation: {r.relation}")
        print(f"  {r.explanation}")