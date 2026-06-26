"""Analysis report for induction: isogroup statistics + grammar compression summary.

Produces a structured, JSON-able report (and a readable text rendering) describing what the learner
found - the order-by-order isogroup counts (cf. paper Fig. 7), the rules it generated, and how much
the input was compressed.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .grammar import Grammar
from .graph import GeometricGraph
from .isogroup import Isogroup


def order_histogram(isogroups: list[Isogroup]) -> dict[int, dict[str, int]]:
    """Per-order summary of detected isogroups: how many, and the most frequent."""
    by_order: dict[int, dict[str, int]] = defaultdict(lambda: {"groups": 0, "max_frequency": 0})
    for iso in isogroups:
        row = by_order[iso.order]
        row["groups"] += 1
        row["max_frequency"] = max(row["max_frequency"], iso.frequency)
    return dict(sorted(by_order.items()))


def grammar_stats(graph: GeometricGraph, grammar: Grammar) -> dict[str, Any]:
    """Compression statistics for a learned grammar."""
    rules = []
    saved = 0
    for r in grammar.rules:
        encoded = len(r.occurrences)
        s = (r.rhs.num_vertices - 1) * encoded
        saved += s
        rules.append({
            "id": r.id,
            "level": r.level,
            "order": r.rhs.num_vertices,
            "edges": r.rhs.num_edges,
            "frequency": r.frequency,
            "encoded_occurrences": encoded,
            "vertices_saved": s,
        })
    original = graph.num_vertices
    axiom_v = grammar.axiom.num_vertices if grammar.axiom is not None else original
    return {
        "input_vertices": original,
        "input_edges": graph.num_edges,
        "rules": rules,
        "levels": (max((r["level"] for r in rules), default=-1) + 1),
        "axiom_vertices": axiom_v,
        "vertices_saved": saved,
        "compression_ratio": (saved / original) if original else 0.0,
    }


def build_report(
    graph: GeometricGraph, isogroups: list[Isogroup], grammar: Grammar
) -> dict[str, Any]:
    return {
        "input": {"vertices": graph.num_vertices, "edges": graph.num_edges},
        "isogroups_by_order": order_histogram(isogroups),
        "grammar": grammar_stats(graph, grammar),
    }


def format_report(report: dict[str, Any]) -> str:
    lines = ["=== G3-2D induction report ==="]
    inp = report["input"]
    lines.append(f"input: {inp['vertices']} vertices, {inp['edges']} edges")

    lines.append("")
    lines.append("isogroups detected (level 0, by order):")
    lines.append("  order   groups   max-frequency")
    for order, row in report["isogroups_by_order"].items():
        lines.append(f"  {order:>5}   {row['groups']:>6}   {row['max_frequency']:>13}")

    g = report["grammar"]
    lines.append("")
    lines.append(f"grammar: {len(g['rules'])} rule(s) across {g['levels']} level(s)")
    lines.append("  rule  lvl  order  edges  freq  encoded  saved")
    for r in g["rules"]:
        lines.append(
            f"  {r['id']:>4}  {r['level']:>3}  {r['order']:>5}  {r['edges']:>5}  "
            f"{r['frequency']:>4}  {r['encoded_occurrences']:>7}  {r['vertices_saved']:>5}"
        )
    lines.append("")
    pct = 100.0 * g["compression_ratio"]
    lines.append(
        f"compression: {g['input_vertices']} V -> axiom {g['axiom_vertices']} V; "
        f"saved {g['vertices_saved']} vertices ({pct:.1f}% of input)"
    )
    return "\n".join(lines)
