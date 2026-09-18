import json

FN_CASE_IDS = ["B_pos_24", "B_pos_25", "B_pos_47", "C_pos_49", "C_pos_58", "C_pos_59"]


def main():
    with open("benchmark_v0.json") as f:
        cases = {c["case_id"]: c for c in json.load(f)["cases"]}

    print("--- FN Triage ---\n")
    for case_id in FN_CASE_IDS:
        case = cases.get(case_id)
        if not case:
            print(f"{case_id}: not found in current benchmark_v0.json (regenerated since last run?)")
            continue
        gt = case["ground_truth"]
        if case_id.startswith("B_"):
            print(f"{case_id}: condition='{gt['condition']}', drug='{gt['drug']}' "
                  f"-> likely CUI-resolution mismatch (same class as B_pos_26/27)")
        else:
            print(f"{case_id}: broad='{gt['broad_condition']}', narrow='{gt['narrow_condition']}' "
                  f"-> likely residual bad mined pair (same class as manual denylist entries)")


if __name__ == "__main__":
    main()