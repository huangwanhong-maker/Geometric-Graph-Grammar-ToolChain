"""Inverse procedural modeling driver (paper Section 4, Fig. 4).

Ties the pipeline together: detect isogroups -> select the best -> cover it with non-overlapping
occurrences -> encode a rule -> rewrite the graph (replace those occurrences with single nodes) ->
repeat on the smaller graph to build hierarchy levels. The result is a ``Grammar`` whose axiom is
the final, most-compressed graph and whose rules regenerate the original.
"""

from __future__ import annotations

from .detection import detect_isogroups
from .encoder import encode_rule
from .expansion import ExpansionParams
from .grammar import Grammar
from .graph import GeometricGraph
from .isogroup import Occurrence
from .isomorphism import DEFAULT_QUANT
from .selection import best_rule


def rewrite(graph: GeometricGraph, occurrences: list[Occurrence], positions) -> GeometricGraph:
    """Replace each occurrence's subgraph with one node, reconnected to external neighbours."""
    g = graph.copy()
    for occ, pos in zip(occurrences, positions, strict=True):
        external = set()
        for v in occ:
            external |= g.neighbors(v)
        external -= set(occ)
        for v in occ:
            g.remove_vertex(v)
        node = g.fresh_vertex_id()
        g.add_vertex(node, pos)
        for x in sorted(external):
            if g.has_vertex(x):
                g.add_edge(node, x)
    return g


def learn(
    graph: GeometricGraph,
    *,
    max_levels: int = 16,
    min_frequency: int = 2,
    frequency_cut: float = 0.0,
    max_order: int | None = 6,
    min_order: int = 2,
    placement: str = "existing",
    prefer: str = "gain",
    quant: float = DEFAULT_QUANT,
    params: ExpansionParams | None = None,
) -> Grammar:
    """Learn a geometric graph grammar from ``graph`` (inverse procedural modeling).

    ``max_order`` bounds the largest pattern searched per level (default 6; ``None`` = unbounded,
    which can be very slow on large inputs). ``quant`` is the geometric similarity tolerance (larger
    groups more approximately-similar structures - raise it for organic/real-world inputs). Each
    level encodes the single best rule (see ``prefer`` in ``selection.best_rule``: ``"gain"`` = max
    compression, ``"dense"`` = prefer closed shapes), rewrites the graph, and repeats for hierarchy.
    """
    g = graph.copy()
    rules = []
    rule_id = 0
    for level in range(max_levels):
        isos = detect_isogroups(
            g, max_order=max_order, min_frequency=min_frequency,
            frequency_cut=frequency_cut, quant=quant, params=params,
        )
        sel = best_rule(isos, prefer=prefer, min_order=min_order)
        if sel is None:  # nothing repeats enough to compress
            break
        iso, cover = sel
        rule = encode_rule(
            g, iso, cover, rule_id=rule_id, level=level, placement=placement, quant=quant
        )
        rules.append(rule)
        rule_id += 1
        g = rewrite(g, cover, [o.node_position for o in rule.occurrences])

    return Grammar(rules=rules, axiom=g, dimension=2)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    from .io import load_json

    parser = argparse.ArgumentParser(description="Learn a geometric graph grammar from a graph.")
    parser.add_argument("graph", help="input graph JSON")
    parser.add_argument("-o", "--out", help="output grammar path (*.ggg.json)")
    parser.add_argument("--max-levels", type=int, default=16)
    parser.add_argument("--min-frequency", type=int, default=2)
    parser.add_argument("--frequency-cut", type=float, default=0.0)
    parser.add_argument("--max-order", type=int, default=None)
    parser.add_argument("--min-order", type=int, default=2,
                        help="skip patterns smaller than this (use 3 to ignore single edges)")
    parser.add_argument(
        "--tolerance", type=float, default=DEFAULT_QUANT,
        help="geometric similarity tolerance (larger = looser; raise for organic/real-world maps)",
    )
    parser.add_argument("--placement", choices=["existing", "centroid"], default="existing")
    parser.add_argument(
        "--prefer", choices=["gain", "dense"], default="gain",
        help="rule ranking: 'gain' = max compression; 'dense' = prefer closed shapes (cycles)",
    )
    parser.add_argument("--text", action="store_true", help="print the human-readable rule dump")
    parser.add_argument(
        "--draw", metavar="PNG",
        help="render the input graph with each level-0 rule's occurrences colour-coded",
    )
    parser.add_argument("--node-size", type=float, default=40.0,
                        help="marker size for --draw (use ~4 for large/dense maps)")
    parser.add_argument("--report", metavar="JSON", help="write the analysis report as JSON")
    parser.add_argument("--quiet", action="store_true", help="don't print the analysis report")
    args = parser.parse_args(argv)

    graph = load_json(args.graph)
    detect_kwargs = dict(
        max_order=args.max_order, min_frequency=args.min_frequency,
        frequency_cut=args.frequency_cut, quant=args.tolerance,
    )
    grammar = learn(
        graph, max_levels=args.max_levels, placement=args.placement,
        prefer=args.prefer, min_order=args.min_order, **detect_kwargs,
    )

    if args.out:
        grammar.save_json(args.out)
        print(f"wrote {args.out}: {grammar}")
    if args.text:
        print(grammar.to_text())

    # analysis report (level-0 isogroups + grammar compression)
    from .analysis import build_report, format_report
    from .detection import detect_isogroups
    report = build_report(graph, detect_isogroups(graph, **detect_kwargs), grammar)
    if not args.quiet:
        print(format_report(report))
    if args.report:
        import json
        from pathlib import Path
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"wrote {args.report}")

    if args.draw:
        from .viz import save_png
        groups = [
            set(o.vertices.values())
            for r in grammar.rules if r.level == 0
            for o in r.occurrences
        ]
        save_png(graph, args.draw, groups=groups, node_size=args.node_size)
        print(f"wrote {args.draw}: {len(groups)} occurrence(s) coloured")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
