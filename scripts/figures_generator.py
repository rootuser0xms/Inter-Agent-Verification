import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.path import Path
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

NAVY = "#002D72"
STEEL_BLUE = "#4589FF"
AMBER = "#FFB000"
TEAL = "#009D9A"
RUST = "#FA4D56"
GRAY = "#8D8D8D"
LIGHT_GRAY = "#F2F2F2"

plt.rcParams["font.family"] = "DejaVu Sans"


def rounded_box(ax, xy, width, height, text, facecolor, textcolor="white",
                 fontsize=11, edgecolor="none", linewidth=0, fontweight="bold",
                 boxstyle="round,pad=0.02,rounding_size=0.08"):
    box = FancyBboxPatch(
        xy, width, height,
        boxstyle=boxstyle,
        linewidth=linewidth, edgecolor=edgecolor, facecolor=facecolor,
        zorder=2,
    )
    ax.add_patch(box)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text,
             ha="center", va="center", fontsize=fontsize, color=textcolor,
             fontweight=fontweight, zorder=3, wrap=True)
    return box


def arrow(ax, start, end, color=GRAY, style="-|>", lw=2, connectionstyle="arc3,rad=0"):
    a = FancyArrowPatch(start, end, arrowstyle=style, color=color,
                         mutation_scale=18, linewidth=lw, zorder=5,
                         connectionstyle=connectionstyle)
    ax.add_patch(a)


def ellipse_node(ax, center, width, height, text, facecolor, fontsize=11.5,
                  dashed=False):
    if dashed:
        # Conditional node (only present in some flows) — light fill,
        # colored dashed border, colored text instead of white-on-solid
        e = mpatches.Ellipse(center, width, height, facecolor="white",
                              edgecolor=facecolor, linewidth=2.2,
                              linestyle="dashed", zorder=2)
        ax.add_patch(e)
        ax.text(center[0], center[1], text, ha="center", va="center",
                 fontsize=fontsize, color=facecolor, fontweight="bold", zorder=3)
    else:
        e = mpatches.Ellipse(center, width, height, facecolor=facecolor,
                              edgecolor="none", zorder=2)
        ax.add_patch(e)
        ax.text(center[0], center[1], text, ha="center", va="center",
                 fontsize=fontsize, color="white", fontweight="bold", zorder=3)


def hexagon_node(ax, center, radius, facecolor, edgecolor, label="Check", fontsize=8,
                  dashed=False):
    h = mpatches.RegularPolygon(center, numVertices=6, radius=radius,
                                 orientation=0, facecolor=facecolor,
                                 edgecolor=edgecolor, linewidth=1.8, zorder=2,
                                 linestyle="dashed" if dashed else "solid")
    ax.add_patch(h)
    if label:
        ax.text(center[0], center[1], label, ha="center", va="center",
                 fontsize=fontsize, color=edgecolor, fontweight="bold", zorder=3)


import matplotlib.patheffects as path_effects


def haloed_text(ax, x, y, text, **kwargs):
    """Text with a white halo, so it stays legible even where a line
    or arc crosses directly underneath it."""
    t = ax.text(x, y, text, **kwargs)
    t.set_path_effects([path_effects.withStroke(linewidth=3, foreground="white")])
    return t


def badge(ax, center, label, text, color):
    bw, bh = 0.42, 0.34
    box = FancyBboxPatch((center[0] - bw / 2, center[1] - bh / 2), bw, bh,
                          boxstyle="round,pad=0.02,rounding_size=0.05",
                          facecolor=color, edgecolor="none", zorder=4)
    ax.add_patch(box)
    ax.text(center[0], center[1], label, ha="center", va="center",
             fontsize=9, color="white", fontweight="bold", zorder=5)
    t = haloed_text(ax, center[0] + 0.35, center[1], text, ha="left", va="center",
                     fontsize=8.5, color="#333333", style="italic", fontweight="bold",
                     zorder=6, linespacing=1.3)


def make_figure1():
    fig, ax = plt.subplots(figsize=(15, 8.5))
    ax.set_xlim(0, 15)
    ax.set_ylim(-1.6, 8.5)
    ax.axis("off")

    ax.text(7.5, 8.1, "Multi-Agent Clinical Hand-off Workflow",
             ha="center", fontsize=17, fontweight="bold", color=NAVY)

    flow_y = 5.6
    node_w, node_h = 1.9, 0.95

    # Start circle
    start_x = 0.6
    ax.add_patch(mpatches.Circle((start_x, flow_y), 0.11, facecolor="black", zorder=3))
    ax.text(start_x, flow_y - 0.4, "Start", ha="center", fontsize=10, fontweight="bold")
    ax.text(start_x - 0.55, flow_y + 0.55, "Patient\npresents", ha="center", fontsize=9,
             color="#4D4D4D", style="italic", linespacing=1.3)
    arrow(ax, (start_x - 0.4, flow_y + 0.3), (start_x, flow_y + 0.05), color=GRAY, lw=1.3)

    agents = [
        ("Triage /\nHistory", NAVY,
         ("1", "Types B/C/D check\n(baseline \u2014 nothing\nprior to compare yet)")),
        ("Diagnostic\nReasoning", STEEL_BLUE,
         ("2", "Types B/C/D check\nvs. everything\nasserted so far")),
        ("Pharmacy\n(Type D flows)", TEAL,
         ("3", "Types B/C/D check\nvs. everything\nasserted so far")),
        ("Treatment /\nBooking", RUST,
         ("4", "Types B/C/D check\nvs. everything\nasserted so far")),
    ]

    captions = [
        "Takes patient history,\nrecords initial findings.",
        "Reasons over findings,\nmay add/revise conditions.",
        "Handles medication\nstatus changes.",
        "Finalizes plan, books\ntreatment/referral.",
    ]

    spacing = 3.15
    xs = [start_x + 1.3 + i * spacing for i in range(4)]

    for i, ((label, color, (num, check_text)), x, caption) in enumerate(zip(agents, xs, captions)):
        is_conditional = (i == 2)  # Pharmacy only appears in Type D flows
        ellipse_node(ax, (x, flow_y), node_w, node_h, label, color, dashed=is_conditional)
        ax.text(x, flow_y - 1.05, caption, ha="center", va="top", fontsize=8.2,
                 color="#333333", style="italic", linespacing=1.3)

       
        hex_x = x + 1.55
        arrow(ax, (x + node_w / 2, flow_y), (hex_x - 0.38, flow_y), color=GRAY, lw=1.6,
              style="-|>" if not is_conditional else "-|>")
        if is_conditional:

            ax.patches[-1].set_linestyle("dashed")
        hexagon_node(ax, (hex_x, flow_y), 0.36, LIGHT_GRAY, color, dashed=is_conditional)

        # numbered badge above the hexagon, describing the check
        badge(ax, (hex_x - 0.55, flow_y + 1.15), num, check_text, color)
        ax.annotate("", xy=(hex_x, flow_y + 0.36), xytext=(hex_x - 0.4, flow_y + 0.95),
                    arrowprops=dict(arrowstyle="-", color=color, lw=1.1, linestyle="dashed"))

        arrow(ax, (hex_x, flow_y - 0.36), (hex_x, flow_y - 0.62), color=RUST, lw=1.3,
              style="-|>")
        haloed_text(ax, hex_x + 0.15, flow_y - 0.5, "No", fontsize=7.5, color=RUST,
                     style="italic", fontweight="bold", zorder=6)

        if i < 3:
            entering_pharmacy = (i == 1)
            arrow(ax, (hex_x + 0.38, flow_y), (xs[i + 1] - node_w / 2, flow_y),
                  color=GRAY, lw=1.6)
            if entering_pharmacy:
                ax.patches[-1].set_linestyle("dashed")
            haloed_text(ax, (hex_x + 0.38 + xs[i + 1] - node_w / 2) / 2, flow_y + 0.28, "Yes",
                         fontsize=7.5, color=TEAL, style="italic", fontweight="bold", ha="center")

    check2_x = xs[1] + 1.55
    treatment_x = xs[3]
    arrow(ax, (check2_x, flow_y + 0.5), (treatment_x, flow_y + node_h / 2 + 0.05),
          color=STEEL_BLUE, lw=1.4, connectionstyle="arc3,rad=-0.4")
    ax.patches[-1].set_linestyle("dashed")
    haloed_text(ax, (check2_x + treatment_x) / 2, flow_y + 2.1,
                 "Types B/C: skip Pharmacy\n(3-hop flow, no Type D check)",
                 fontsize=8, color=STEEL_BLUE, style="italic", fontweight="bold",
                 ha="center", linespacing=1.3)

    # End circle
    end_x = xs[-1] + 3.0
    arrow(ax, (xs[-1] + 1.55 + 0.38, flow_y), (end_x - 0.11, flow_y), color=GRAY, lw=1.6)
    haloed_text(ax, (xs[-1] + 1.93 + end_x - 0.11) / 2, flow_y + 0.28, "Yes",
                 fontsize=7.5, color=TEAL, style="italic", fontweight="bold", ha="center")
    ax.add_patch(mpatches.Circle((end_x, flow_y), 0.11, facecolor="black", zorder=3))
    ax.text(end_x, flow_y - 0.4, "End", ha="center", fontsize=10, fontweight="bold")

    # Assertion store band along the bottom, fed by every Yes/No outcome
    store_y = 1.0
    rounded_box(ax, (start_x, store_y), end_x - start_x, 0.85,
                "Assertion Store  (running, ontology-anchored claims in hand-off order)",
                LIGHT_GRAY, textcolor=NAVY, fontsize=10.5, fontweight="bold")
    for x in xs:
        hex_x = x + 1.55
        arrow(ax, (hex_x, flow_y - 0.4), (hex_x, store_y + 0.87), color=AMBER, lw=1.2,
              connectionstyle="arc3,rad=0.15")

    note_y = -0.5
    ax.add_patch(mpatches.Circle((0.5, note_y), 0.07, facecolor=RUST))
    ax.text(0.75, note_y, "Any \"No\" is logged as a Contradiction Flagged record "
                            "(pipeline continues \u2014 it does not halt or retry)",
             fontsize=8.5, color="#4D4D4D", va="center", ha="left", style="italic")

    # Legend
    leg_y = -1.15
    ax.add_patch(mpatches.Circle((0.5, leg_y), 0.08, facecolor="black"))
    ax.text(0.75, leg_y, "Start / End", fontsize=8.5, va="center")
    ellipse_node(ax, (2.7, leg_y), 0.9, 0.4, "Agent", NAVY, fontsize=7.5)
    ax.text(3.35, leg_y, "Agent phase", fontsize=8.5, va="center")
    hexagon_node(ax, (5.9, leg_y), 0.22, LIGHT_GRAY, GRAY, label=None)
    ax.text(6.25, leg_y, "Consistency check\n(every hand-off)", fontsize=8.5, va="center",
             linespacing=1.2)
    badge(ax, (9.3, leg_y), "N", "Numbered check\ncriterion", GRAY)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "figure1_architecture.png"),
                dpi=360, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Figure 1 saved.")


def relation_chip(ax, x, y, text, color):
    bw = min(0.11 * len(text) + 0.2, 1.5)
    bh = 0.3
    box = FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh,
                          boxstyle="round,pad=0.02,rounding_size=0.06",
                          facecolor=color, edgecolor="none", zorder=4)
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=6.8, color="white",
             fontweight="bold", zorder=5)
    return bw


def make_figure2():
    fig, ax = plt.subplots(figsize=(14, 7.4))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7.4)
    ax.axis("off")

    ax.text(7, 6.95, "Semantic Contradiction Taxonomy",
             ha="center", fontsize=17, fontweight="bold", color=NAVY)
    ax.text(7, 6.5, "Four contradiction types checked at every inter-agent hand-off",
             ha="center", fontsize=10, color="#666666", style="italic")

    card_w, card_h = 3.05, 5.7
    card_y = 0.4
    gap = 0.28
    total_w = 4 * card_w + 3 * gap
    start_x = (14 - total_w) / 2
    card_xs = [start_x + i * (card_w + gap) for i in range(4)]

    cards = [
        ("A", "Mutual\nExclusion", GRAY, True, "none found",
         "Sibling diagnoses under a\npinned parent concept.",
         "Scoped out of v0.1 \u2014 no\nvalidated UMLS relation\nfound. Documented as\nreal future work.", None),
        ("B", "Contraindication", RUST, False, "has_contraindicated_drug",
         "A later agent recommends\na drug contraindicated by\nan earlier condition.",
         "Example:\nkidney disease \u2192\nergotamine\n(source: MED-RT)", None),
        ("C", "Hierarchical\nInconsistency", STEEL_BLUE, False, "isa",
         "A later agent asserts a\nsubtype of a condition\nexcluded earlier.",
         'Example:\n"no kidney disease" \u2192\nkidney/ureter disorder\n(source: SNOMED CT)', None),
        ("D", "Temporal\nSupersession", TEAL, False, "assertion timeline",
         "A later agent relies on a\nstatus already superseded\nby an intervening update.",
         "No ontology lookup \u2014\npure assertion-store logic.",
         ["Medication status\n(active \u2194 discontinued)", "Condition status\n(present \u2194 ruled out)"]),
    ]

    for (letter, name, color, dashed, relation, mechanism, example, sublist), x in zip(cards, card_xs):
        cx = x + card_w / 2

        # Card background
        if dashed:
            outer = FancyBboxPatch((x, card_y), card_w, card_h,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    linewidth=2, edgecolor=color, facecolor="white",
                                    linestyle="dashed", zorder=2)
        else:
            outer = FancyBboxPatch((x, card_y), card_w, card_h,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    linewidth=1.5, edgecolor=color, facecolor="white",
                                    zorder=2)
        ax.add_patch(outer)

        header_h = 1.15
        header_y = card_y + card_h - header_h
        header = FancyBboxPatch((x, header_y), card_w, header_h,
                                 boxstyle="round,pad=0.02,rounding_size=0.06",
                                 facecolor=("white" if dashed else color),
                                 edgecolor=(color if dashed else "none"),
                                 linestyle=("dashed" if dashed else "solid"),
                                 linewidth=(2 if dashed else 0), zorder=3)
        ax.add_patch(header)
        ax.add_patch(mpatches.Rectangle((x, header_y), card_w, header_h * 0.35,
                                         facecolor=("white" if dashed else color),
                                         edgecolor="none", zorder=2.5))

        letter_color = color if dashed else "white"
        name_color = color if dashed else "white"
        ax.text(x + 0.22, header_y + header_h - 0.32, f"Type {letter}",
                 fontsize=10.5, color=letter_color, fontweight="bold", ha="left", va="top")
        ax.text(x + 0.22, header_y + header_h - 0.68, name, fontsize=13,
                 color=name_color, fontweight="bold", ha="left", va="top", linespacing=1.05)

        chip_y = header_y - 0.28
        chip_w = min(0.1 * len(relation) + 0.2, card_w - 0.4)
        chip = FancyBboxPatch((cx - chip_w / 2, chip_y - 0.15), chip_w, 0.3,
                               boxstyle="round,pad=0.02,rounding_size=0.05",
                               facecolor=(LIGHT_GRAY if dashed else color), alpha=1,
                               edgecolor=(color if dashed else "none"),
                               linewidth=(1.2 if dashed else 0), zorder=4)
        ax.add_patch(chip)
        ax.text(cx, chip_y, relation, ha="center", va="center", fontsize=7.3,
                 color=(color if dashed else "white"), fontweight="bold", zorder=5)

        # Mechanism description
        mech_y = chip_y - 0.55
        ax.text(x + 0.22, mech_y, mechanism, ha="left", va="top", fontsize=8.5,
                 color="#333333", linespacing=1.35)

        # Divider line
        div_y = mech_y - 0.9
        ax.plot([x + 0.22, x + card_w - 0.22], [div_y, div_y], color="#DDDDDD", lw=1, zorder=2)

        # Example / detail text
        ex_y = div_y - 0.22
        ax.text(x + 0.22, ex_y, example, ha="left", va="top", fontsize=8.2,
                 color="#555555", style="italic", linespacing=1.35)

        if sublist:
            sub_y = ex_y - 1.0
            ax.plot([x + 0.22, x + card_w - 0.22], [sub_y + 0.18, sub_y + 0.18],
                     color="#DDDDDD", lw=1, zorder=2)
            for j, item in enumerate(sublist):
                iy = sub_y - j * 0.62
                ax.text(x + 0.3, iy, "\u2192", fontsize=9, color=color, fontweight="bold",
                         ha="left", va="top")
                ax.text(x + 0.55, iy, item, ha="left", va="top", fontsize=7.8,
                         color="#444444", linespacing=1.2)

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "figure2_taxonomy.png"),
                dpi=360, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Figure 2 saved.")



def panel_header(ax, x, y, w, h, header_h, title, header_color, body_color):
    outer = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                            facecolor=body_color, edgecolor=header_color, linewidth=1.6, zorder=2)
    ax.add_patch(outer)
    header = FancyBboxPatch((x, y + h - header_h), w, header_h,
                             boxstyle="round,pad=0.02,rounding_size=0.08",
                             facecolor=header_color, edgecolor="none", zorder=3)
    ax.add_patch(header)
    ax.add_patch(mpatches.Rectangle((x, y + h - header_h), w, header_h * 0.4,
                                     facecolor=header_color, edgecolor="none", zorder=2.5))
    ax.text(x + w / 2, y + h - header_h / 2, title, ha="center", va="center",
             fontsize=11.5, color="white", fontweight="bold", zorder=4)
    return y + h - header_h


def subbox(ax, x, y, w, h, lines, edge_color, header_line=None, header_color=None, center=False):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.05",
                          facecolor="white", edgecolor=edge_color, linewidth=1.2, zorder=3)
    ax.add_patch(box)
    if center:
        n_lines = len(lines) + (1 if header_line else 0)
        line_h = 0.32
        block_h = n_lines * line_h
        ty = y + h / 2 + block_h / 2 - line_h / 2
        if header_line:
            ax.text(x + w / 2, ty, header_line, ha="center", va="center", fontsize=9,
                     color=header_color or edge_color, fontweight="bold", zorder=4)
            ty -= line_h
        for ln in lines:
            bold = ln.startswith("**")
            txt = ln.replace("**", "")
            ax.text(x + w / 2, ty, txt, ha="center", va="center", fontsize=8.3,
                     color="#222222", fontweight="bold" if bold else "normal",
                     style="italic" if ln.startswith("*i*") else "normal", zorder=4)
            ty -= line_h
        return y
    ty = y + h - 0.18
    if header_line:
        ax.text(x + w / 2, ty, header_line, ha="center", va="top", fontsize=9,
                 color=header_color or edge_color, fontweight="bold", zorder=4)
        ty -= 0.32
    for ln in lines:
        bold = ln.startswith("**")
        txt = ln.replace("**", "")
        ax.text(x + 0.15, ty, txt, ha="left", va="top", fontsize=8.3,
                 color="#222222", fontweight="bold" if bold else "normal",
                 style="italic" if ln.startswith("*i*") else "normal", zorder=4)
        ty -= 0.3
    return y


def label_above(ax, x, y, text, color):
    ax.text(x, y, text, ha="left", va="bottom", fontsize=8.5, color=color, fontweight="bold")


def small_arrow_down(ax, x, y1, y2, color=GRAY):
    arrow(ax, (x, y1), (x, y2), color=color, lw=1.6)


def diamond_node(ax, cx, cy, w, h, label, color):
    d = mpatches.RegularPolygon((cx, cy), numVertices=4, radius=w / 2, orientation=0.785398,
                                 facecolor="#E8F8F5", edgecolor=color, linewidth=1.6, zorder=3)
    ax.add_patch(d)
    ax.text(cx, cy, label, ha="center", va="center", fontsize=8.5, color=color,
             fontweight="bold", zorder=4)


def make_figure3():
    fig, ax = plt.subplots(figsize=(20, 13.5))
    ax.set_xlim(0, 20.3)
    ax.set_ylim(0, 13.7)
    ax.axis("off")

    ax.text(10.15, 13.35, "Concrete Data Transformation and Verification Trace",
             ha="center", fontsize=19, fontweight="bold", color="#1A1A2E")
    ax.text(10.15, 12.85, "Step-by-step trace of raw clinical text parsed, grounded, stored, and evaluated for inter-agent contradiction",
             ha="center", fontsize=10.5, color="#666666", style="italic")

    panel_w, panel_h, header_h = 4.55, 8.6, 0.75
    gap = 0.35
    xs = [0.3 + i * (panel_w + gap) for i in range(4)]
    panel_y = 3.5

    # ---------- STAGE 1 ----------
    c1 = NAVY
    panel_header(ax, xs[0], panel_y, panel_w, panel_h, header_h, "STAGE 1: LLM Claim Extraction", c1, "#EAF1FB")
    top = panel_y + panel_h - header_h - 0.25
    label_above(ax, xs[0] + 0.15, top, "Raw Agent Text (Hop t=2):", c1)
    subbox(ax, xs[0] + 0.15, top - 1.35, panel_w - 0.3, 1.05,
           ['"Recommend ergotamine for\nmigraine relief."'], c1, center=True)
    small_arrow_down(ax, xs[0] + panel_w / 2, top - 1.43, top - 1.87, STEEL_BLUE)
    subbox(ax, xs[0] + 0.55, top - 2.55, panel_w - 1.1, 0.6,
           ["Engine: Local Llama 3.1 8B"], STEEL_BLUE, center=True)
    small_arrow_down(ax, xs[0] + panel_w / 2, top - 2.63, top - 3.52, STEEL_BLUE)
    label_above(ax, xs[0] + 0.15, top - 3.35, "Extracted 6-Tuple Assertion:", c1)
    subbox(ax, xs[0] + 0.15, top - 4.65, panel_w - 0.3, 1.05,
           ["\u03b1\u2082 = (Patient, recommends_medication,", '"ergotamine", false, t=2, \u2205)'], c1, center=True)

    # ---------- STAGE 2 ----------
    c2 = TEAL
    panel_header(ax, xs[1], panel_y, panel_w, panel_h, header_h, "STAGE 2: Hybrid UMLS Grounding", c2, "#E9F7F5")
    top2 = panel_y + panel_h - header_h - 0.25
    label_above(ax, xs[1] + 0.15, top2, 'Input Term: "ergotamine"', c2)
    subbox(ax, xs[1] + 0.15, top2 - 1.15, panel_w - 0.3, 0.85,
           ["1. Pinned Seed Dictionary\n(exact-match lookup)"], c2, center=True)
    small_arrow_down(ax, xs[1] + panel_w / 2, top2 - 1.23, top2 - 1.72, c2)
    dcx, dcy = xs[1] + panel_w / 2, top2 - 2.35
    diamond_node(ax, dcx, dcy, 1.1, 1.1, "Match\nFound?", c2)
    diamond_right = dcx + 0.55
    fallback_left = xs[1] + panel_w - 1.4
    arrow(ax, (diamond_right, dcy), (fallback_left, dcy), color=AMBER, lw=2.0)
    haloed_text(ax, (diamond_right + fallback_left) / 2, dcy + 0.16, "No",
                 fontsize=8, color=AMBER, fontweight="bold", ha="center")
    subbox(ax, fallback_left, dcy - 0.45, 1.3, 0.9,
           ["2. Fallback:\nLive UMLS\nSearch API"], AMBER, center=True)
    small_arrow_down(ax, dcx, dcy - 0.63, dcy - 1.22, c2)
    haloed_text(ax, dcx + 0.28, dcy - 0.85, "Yes", fontsize=8, color=c2, fontweight="bold")
    arrow(ax, (fallback_left + 0.65, dcy - 0.53), (dcx + 0.35, dcy - 1.22),
          color=AMBER, lw=1.4)
    subbox(ax, xs[1] + 0.15, dcy - 2.35, panel_w - 0.3, 1.05,
           ["Anchored via live UMLS search", "(ergotamine \u2014 not one of this\nproject's 16 pinned conditions)"], c2, center=True)

    # ---------- STAGE 3 ----------
    c3 = "#5B4B9E"
    panel_header(ax, xs[2], panel_y, panel_w, panel_h, header_h, "STAGE 3: Assertion Store Memory", c3, "#F0EDF9")
    top3 = panel_y + panel_h - header_h - 0.3
    bx, by, bw, bh = xs[2] + 0.15, top3 - 6.9, panel_w - 0.3, 6.9
    box = FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.02,rounding_size=0.05",
                          facecolor="white", edgecolor=c3, linewidth=1.2, zorder=3)
    ax.add_patch(box)
    ty = by + bh - 0.35
    ax.text(bx + bw / 2, ty, "Cumulative Store  S\u2082 = { \u03b1\u2081, \u03b1\u2082 }",
             ha="center", va="top", fontsize=10, color=c3, fontweight="bold", zorder=4)
    ty -= 0.55
    ax.plot([bx + 0.2, bx + bw - 0.2], [ty, ty], color="#CCCCCC", lw=1, zorder=4)
    ty -= 0.35
    ax.text(bx + 0.2, ty, "Prior Assertion \u03b1\u2081 (Hop t=1):", ha="left", va="top",
             fontsize=9, color=c3, fontweight="bold", zorder=4)
    for ln in ['Subject: Patient', 'Predicate: has_condition', 'Object: "kidney disease"', "CUI: C0022658"]:
        ty -= 0.32
        ax.text(bx + 0.35, ty, "\u2022 " + ln, ha="left", va="top", fontsize=8.3, color="#222222", zorder=4)
    ty -= 0.45
    ax.plot([bx + 0.2, bx + bw - 0.2], [ty, ty], color="#CCCCCC", lw=1, zorder=4)
    ty -= 0.35
    ax.text(bx + 0.2, ty, "New Assertion \u03b1\u2082 (Hop t=2):", ha="left", va="top",
             fontsize=9, color="#B23A48", fontweight="bold", zorder=4)
    for ln in ['Subject: Patient', 'Predicate: recommends_medication', 'Object: "ergotamine"', "CUI: (resolved live via UMLS)"]:
        ty -= 0.32
        ax.text(bx + 0.35, ty, "\u2022 " + ln, ha="left", va="top", fontsize=8.3, color="#222222", zorder=4)

    # ---------- STAGE 4 ----------
    c4 = RUST
    panel_header(ax, xs[3], panel_y, panel_w, panel_h, header_h, "STAGE 4: Semantic Verifier", c4, "#FCEBEC")
    top4 = panel_y + panel_h - header_h - 0.25
    bx4, by4, bh4 = xs[3] + 0.15, top4 - 2.55, 2.3
    box4 = FancyBboxPatch((bx4, by4), panel_w - 0.3, bh4, boxstyle="round,pad=0.02,rounding_size=0.05",
                           facecolor="white", edgecolor=c4, linewidth=1.2, zorder=3)
    ax.add_patch(box4)
    ty4 = by4 + bh4 - 0.3
    ax.text(bx4 + (panel_w - 0.3) / 2, ty4, "Semantic Verifier Logic", ha="center", va="top",
             fontsize=9.5, color=c4, fontweight="bold", zorder=4)
    ty4 -= 0.35
    for ln in ["Relation: Type B (Contraindication)", "Query: MED-RT relation"]:
        ax.text(bx4 + 0.15, ty4, "\u2022 " + ln, ha="left", va="top", fontsize=8.3, color="#222222", zorder=4)
        ty4 -= 0.32
    ax.text(bx4 + (panel_w - 0.3) / 2, ty4 - 0.05, "has_contraindicated_drug",
             ha="center", va="top", fontsize=9, color=c4, fontweight="bold", zorder=4)
    small_arrow_down(ax, xs[3] + panel_w / 2, by4 - 0.08, by4 - 0.57, c4)
    vy, vh = by4 - 0.65 - 2.4, 2.4
    vbox = FancyBboxPatch((bx4, vy), panel_w - 0.3, vh, boxstyle="round,pad=0.02,rounding_size=0.05",
                           facecolor="#FCEBEC", edgecolor=c4, linewidth=2, zorder=3)
    ax.add_patch(vbox)
    ax.text(bx4 + (panel_w - 0.3) / 2, vy + vh - 0.35, "VERDICT RETURNED:", ha="center", va="top",
             fontsize=8.7, color=c4, fontweight="bold", zorder=4)
    ax.text(bx4 + (panel_w - 0.3) / 2, vy + vh - 0.72, "CONTRADICTION FLAGGED", ha="center", va="top",
             fontsize=11, color=c4, fontweight="bold", zorder=4)
    ax.text(bx4 + (panel_w - 0.3) / 2, vy + vh - 1.35,
             "Ergotamine (\u03b1\u2082) is contraindicated for\nkidney disease, C0022658 (\u03b1\u2081)\nper MED-RT has_contraindicated_drug",
             ha="center", va="top", fontsize=8, color="#333333", style="italic", zorder=4)

    for i in range(3):
        arrow(ax, (xs[i] + panel_w + 0.03, panel_y + panel_h - header_h / 2),
              (xs[i + 1] - 0.03, panel_y + panel_h - header_h / 2), color="#444444", lw=1.8)

    # ---------- SUMMARY BAR ----------
    sum_y, sum_h, sum_header_h = 0.95, 2.35, 0.55
    sw = xs[3] + panel_w - xs[0]
    sbox = FancyBboxPatch((xs[0], sum_y), sw, sum_h, boxstyle="round,pad=0.02,rounding_size=0.04",
                           facecolor="white", edgecolor="#333344", linewidth=1.4, zorder=2)
    ax.add_patch(sbox)
    shead = FancyBboxPatch((xs[0], sum_y + sum_h - sum_header_h), sw, sum_header_h,
                            boxstyle="round,pad=0.02,rounding_size=0.04", facecolor="#2C3E50",
                            edgecolor="none", zorder=3)
    ax.add_patch(shead)
    ax.add_patch(mpatches.Rectangle((xs[0], sum_y + sum_h - sum_header_h), sw, sum_header_h * 0.4,
                                     facecolor="#2C3E50", edgecolor="none", zorder=2.5))
    ax.text(xs[0] + sw / 2, sum_y + sum_h - sum_header_h / 2,
             "End-to-End Clinical Hand-off Contradiction Detection Flow",
             ha="center", va="center", fontsize=11, color="white", fontweight="bold", zorder=4)

    cols = [
        ("1. Extraction and Parsing", NAVY, [
            "Raw unstructured text parsed by local LLM",
            "Extracted into formal 6-tuple \u03b1 = (s, p, o, \u00ac, t, c)",
            "Preserves negation status and hop index",
            "Local Llama 3.1 8B: zero API cost, no data leaves machine"]),
        ("2. Hybrid Ontology Grounding", TEAL, [
            "Pinned seed dictionary maps known terms to CUIs",
            "Live UMLS concept search used as fallback",
            "Grounds object text to a UMLS Concept Unique Identifier",
            "Standardizes terms across heterogeneous agents"]),
        ("3. Cumulative Verification", RUST, [
            "Appends assertion to session Assertion Store S_t",
            "Evaluates against all prior assertions across hops",
            "Queries MED-RT / SNOMED CT ontology relations",
            "Surfaces contradiction flag with explicit relation"]),
    ]
    col_w = sw / 3
    for j, (title, color, bullets) in enumerate(cols):
        cx0 = xs[0] + j * col_w + 0.25
        cy = sum_y + sum_h - sum_header_h - 0.3
        ax.text(cx0, cy, title, ha="left", va="top", fontsize=10, color=color, fontweight="bold", zorder=4)
        cy -= 0.32
        for b in bullets:
            ax.text(cx0, cy, "\u2022 " + b, ha="left", va="top", fontsize=7.8, color="#333333", zorder=4)
            cy -= 0.24

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "figure3_pipeline.png"),
                dpi=360, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Figure 3 saved.")


if __name__ == "__main__":
    make_figure1()
    make_figure2()
    make_figure3()