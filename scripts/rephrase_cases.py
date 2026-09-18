import json
import requests
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"

REPHRASE_PROMPT = """You are rewriting a single sentence from a clinical AI agent's note, for phrasing variety in a test dataset.

CRITICAL RULES — violating any of these makes the output useless:
1. Do NOT change, drop, or add any condition name, drug name, or medical term.
2. Do NOT change whether something is negated/denied/ruled-out vs. asserted/present. If the original says "no evidence of X" or "ruled out X", the rewrite must still clearly deny X. If the original asserts X as present, the rewrite must still clearly assert X.
3. Keep the same clinical meaning exactly — only vary sentence structure, word choice, and phrasing style.
4. Keep it roughly the same length (one to two sentences).
5. Return ONLY the rewritten sentence, nothing else — no preamble, no quotes, no explanation.

Original sentence:
{original_text}
"""


def rephrase(text: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": REPHRASE_PROMPT.format(original_text=text),
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 200},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["response"].strip().strip('"')


def main():
    with open(os.path.join(DATA_DIR, "benchmark_v0.json")) as f:
        data = json.load(f)

    rephrased_cases = []
    for i, case in enumerate(data["cases"], 1):
        print(f"[{i}/{len(data['cases'])}] Rephrasing {case['case_id']}...")
        new_hops = []
        for hop in case["hops"]:
            original = hop["text"]
            try:
                new_text = rephrase(original)
            except Exception as e:
                print(f"  ERROR rephrasing hop {hop['hop_index']}: {e} — keeping original text")
                new_text = original
            new_hops.append({**hop, "text": new_text, "original_text": original})
        rephrased_cases.append({**case, "hops": new_hops})

    with open(os.path.join(DATA_DIR, "benchmark_v0_rephrased.json"), "w") as f:
        json.dump({"cases": rephrased_cases, "mining_report": data.get("mining_report", {})}, f, indent=2)
    print(f"\nSaved {len(rephrased_cases)} rephrased cases to data/benchmark_v0_rephrased.json")
    print("Original data/benchmark_v0.json is UNCHANGED.")


if __name__ == "__main__":
    main()