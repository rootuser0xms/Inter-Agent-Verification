import json
import requests

from umls_client import search_concept, get_concept  # our module from earlier
from models import Assertion
from pinned_concepts import PINNED_CONDITIONS

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b" 

EXTRACTION_PROMPT = """You are extracting structured clinical assertions from a single agent's output in a multi-agent clinical AI pipeline.

Given the agent's text, extract EVERY DISTINCT clinical claim as a separate JSON object — the text below likely contains MULTIPLE claims (e.g. an allergy statement AND a condition AND a medication), and you must return one object per claim, not just the first or most prominent one.

Each object needs these fields:
- "subject": almost always "patient" unless the claim is about something else
- "predicate": one of: has_condition, excludes_condition, has_allergy, no_known_allergy, takes_medication, discontinued_medication, has_finding, recommends_treatment, recommends_medication
- "object_text": the clinical term itself, as plainly stated as possible (e.g. "penicillin allergy", "type 2 diabetes mellitus") — normalize casing/phrasing slightly for searchability but don't paraphrase away clinical meaning
- "negated": true if the claim is a denial/absence (e.g. "no known allergies" -> negated: true, object_text: "known allergies"), false otherwise

Return ONLY a JSON array of these objects, nothing else — no preamble, no markdown fences, no explanation.

Agent text:
{agent_text}
"""


CLAIM_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "predicate": {
                "type": "string",
                "enum": [
                    "has_condition", "excludes_condition", "has_allergy",
                    "no_known_allergy", "takes_medication",
                    "discontinued_medication", "has_finding",
                    "recommends_treatment", "recommends_medication",
                ],
            },
            "object_text": {"type": "string"},
            "negated": {"type": "boolean"},
        },
        "required": ["subject", "predicate", "object_text", "negated"],
    },
}


def extract_claims(agent_text: str, debug: bool = True) -> list[dict]:
    """First pass: free text -> structured (unanchored) claims via local Ollama."""
    payload = {
        "model": MODEL_NAME,
        "prompt": EXTRACTION_PROMPT.format(agent_text=agent_text),
        "stream": False,
        "format": CLAIM_SCHEMA,  # explicit schema — forces an ARRAY shape,
        "options": {
            "num_predict": 800,
            "temperature": 0.0,
        },
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    raw = resp.json()["response"].strip()

    if debug:
        print("--- RAW MODEL OUTPUT (debug) ---")
        print(raw)
        print("--- END RAW OUTPUT ---\n")

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        # fallback, shouldn't trigger now that schema forces array shape
        for value in parsed.values():
            if isinstance(value, list):
                return value
        return [parsed]
    return parsed


def anchor_to_ontology(object_text: str) -> dict:
    pinned_cui = PINNED_CONDITIONS.get(object_text.lower().strip())
    if pinned_cui:
        concept = get_concept(pinned_cui)
        return {
            "ontology_code": pinned_cui,
            "ontology_name": concept["name"],
            "ontology_source": "PINNED",
        }

    results = search_concept(object_text)
    if not results:
        return {"ontology_code": None, "ontology_name": None, "ontology_source": None}
    top = results[0]
    return {
        "ontology_code": top.get("ui"),
        "ontology_name": top.get("name"),
        "ontology_source": top.get("rootSource"),
    }


def process_agent_output(agent_text: str, agent_id: str, hop_index: int, debug: bool = False) -> list[Assertion]:
    """Full pipeline: text -> structured claims -> ontology-anchored assertions."""
    raw_claims = extract_claims(agent_text, debug=debug)
    assertions = []
    for claim in raw_claims:
        anchor = anchor_to_ontology(claim["object_text"])
        assertions.append(Assertion(
            subject=claim.get("subject", "patient"),
            predicate=claim["predicate"],
            object_text=claim["object_text"],
            negated=claim.get("negated", False),
            agent_id=agent_id,
            hop_index=hop_index,
            **anchor
        ))
    return assertions


if __name__ == "__main__":
    test_text = "Patient reports no known drug allergies. History of type 2 diabetes mellitus, well-controlled on metformin."
    results = process_agent_output(test_text, agent_id="triage_agent", hop_index=1, debug=True)
    for a in results:
        print(a)