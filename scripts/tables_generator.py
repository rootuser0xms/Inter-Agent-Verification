
import json
import os
import textwrap
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "tables")
os.makedirs(OUTPUT_DIR, exist_ok=True)
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

NAVY = "#002D72"
LIGHT_GRAY = "#F2F2F2"
WHITE = "white"


def load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"MISSING: {filename} — run the script that produces it first (see this "
              f"file's docstring). Skipping tables that need it.")
        return None
    with open(path) as f:
        return json.load(f)


def wrap_cell(text: str, width: int) -> str:

    lines = []
    for segment in str(text).split("\n"):
        lines.extend(textwrap.wrap(segment, width=width) or [""])
    return "\n".join(lines)


def save_table(rows: list[list[str]], header: list[str], name: str, title: str,
               col_fractions: list[float], char_widths: list[int]):
    total = sum(col_fractions)
    col_fractions = [f / total for f in col_fractions]

    wrapped_header = [wrap_cell(h, w) for h, w in zip(header, char_widths)]
    wrapped_rows = [[wrap_cell(c, w) for c, w in zip(row, char_widths)] for row in rows]

    lines_per_row = [max(cell.count("\n") + 1 for cell in row) for row in wrapped_rows]
    header_lines = max(h.count("\n") + 1 for h in wrapped_header)

    fig_w = 13

    fig_h = 1.0 + 0.35 * header_lines + sum(0.32 * n for n in lines_per_row) + 0.6

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(title, fontsize=15, fontweight="bold", color=NAVY, pad=18)

    table = ax.table(cellText=wrapped_rows, colLabels=wrapped_header, cellLoc="center",
                      loc="center", colWidths=col_fractions, bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)

    row_scale = 1.0 + 0.55 * max(max(lines_per_row), header_lines)
    table.scale(1, row_scale)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#DDDDDD")
        cell.set_text_props(va="center", ha="center")
        if r == 0:
            cell.set_facecolor(NAVY)
            cell.set_text_props(color="white", fontweight="bold", va="center", ha="center")
        else:
            cell.set_facecolor(LIGHT_GRAY if r % 2 == 0 else WHITE)

    fig.savefig(os.path.join(OUTPUT_DIR, f"{name}.png"), dpi=360,
                bbox_inches="tight", facecolor="white", pad_inches=0.3)
    plt.close(fig)
    print(f"Saved {name}.png")


def build_table1():
    benchmark = load_json("benchmark_v0.json")

    def find_example(type_code, fields):
        if not benchmark:
            return "N/A (run benchmark_generator.py)"
        for case in benchmark["cases"]:
            gt = case["ground_truth"]
            if gt.get("type") == type_code and gt.get("contradiction_present"):
                return " -> ".join(gt[f] for f in fields)
        return "no example found"

    rows = [
        ["A", "Mutual\nExclusion",
         "Two condition assertions that are mutually exclusive primary "
         "classifications (sibling diagnoses under a shared parent)",
         "Scoped out of v0.1 - no validated data source found (see limitations)",
         "High\n(future work)"],
        ["B", "Contraindication",
         "A later agent asserts/recommends a drug that is contraindicated given "
         "an earlier-established condition",
         find_example("B", ["condition", "drug"]),
         "High"],
        ["C", "Hierarchical\nInconsistency",
         "A later agent asserts a specific condition that is a subtype of a "
         "broader condition explicitly excluded earlier",
         find_example("C", ["broad_condition", "narrow_condition"]),
         "Medium"],
        ["D", "Temporal\nSupersession",
         "A later agent relies on a status (medication/condition) that has "
         "already been superseded by an intervening retraction",
         find_example("D", ["drug"]) + " (discontinued, then re-recommended)",
         "High"],
    ]
    save_table(
        rows,
        ["Type", "Category", "Formal Definition", "Real Example", "Severity*"],
        "Table1", "Table 1: Semantic Contradiction Taxonomy",
        col_fractions=[0.6, 1.9, 3.9, 3.3, 1.4],
        char_widths=[6, 17, 42, 36, 14],
    )
    print("  *Severity is author-assigned clinical judgment for illustration, "
          "NOT empirically derived from the benchmark.")


def build_table2():
    ours_clean = load_json("benchmark_results.json")
    ours_rephrased = load_json("benchmark_results_rephrased.json")
    regex_clean = load_json("regex_results.json")
    regex_rephrased = load_json("regex_results_rephrased.json")
    single_clean = load_json("ablation_results.json")
    single_rephrased = load_json("ablation_results_rephrased.json")

    def pct(d):
        if d is None:
            return "N/A"
        source = d.get("summary", d)
        val = source.get("catch_rate")
        return f"{val:.1%}" if val is not None else "N/A"

    rows = [
        ["Single-agent grounding\n(prior-art style)",
         pct(single_clean), pct(single_rephrased),
         "Flags only ungrounded terms - cannot see cross-hop relationships. "
         "Rephrased score is SPURIOUS (see notes)."],
        ["Regex (privileged -\nhardcoded exact answers)",
         pct(regex_clean), pct(regex_rephrased),
         "Most generous possible rule-based baseline; brittle to phrasing "
         "despite perfect advance knowledge."],
        ["Ours (inter-agent,\nontology-grounded)",
         pct(ours_clean), pct(ours_rephrased),
         "No advance knowledge of answers; generalizes via live ontology "
         "relations, not string matching."],
    ]
    save_table(
        rows, ["Method", "Clean Catch Rate", "Rephrased Catch Rate", "Notes"],
        "Table2", "Table 2: Quantitative Performance Comparison",
        col_fractions=[2.2, 1.4, 1.6, 3.8],
        char_widths=[22, 12, 14, 42],
    )
    print("  Note: single-agent grounding's rephrased-text score is spurious - ")


def build_table3():
    for label, filename, out_name in [
        ("Clean (templated)", "benchmark_results.json", "Table3_Clean"),
        ("Rephrased (natural)", "benchmark_results_rephrased.json", "Table3_Rephrased"),
    ]:
        data = load_json(filename)
        if data is None:
            continue
        detailed = data["detailed"]
        rows = []
        for type_code in ["B", "C", "D"]:
            type_cases = [d for d in detailed if d.get("expected_type") == type_code]
            tp = sum(1 for d in type_cases if d["status"] == "TP")
            fn = sum(1 for d in type_cases if d["status"] == "FN")
            n = tp + fn
            recall = tp / n if n else None
            precision = 1.0 if tp > 0 or fn == 0 else None
            f1 = (2 * precision * recall / (precision + recall)
                  if precision and recall and (precision + recall) > 0 else
                  (0.0 if recall == 0 else None))
            rows.append([
                type_code, str(n),
                f"{precision:.1%}" if precision is not None else "N/A",
                f"{recall:.1%}" if recall is not None else "N/A",
                f"{f1:.1%}" if f1 is not None else "N/A",
            ])
        save_table(
            rows, ["Type", "N", "Precision", "Recall", "F1"],
            out_name, f"Table 3: Per-Type Breakdown - {label}",
            col_fractions=[1.0, 1.4, 1.6, 1.6, 1.4],
            char_widths=[8, 10, 12, 12, 12],
        )


if __name__ == "__main__":
    print("=== Table 1 ===")
    build_table1()
    print("\n=== Table 2 ===")
    build_table2()
    print("\n=== Table 3 ===")
    build_table3()