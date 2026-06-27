"""Syntax analysis: parse a geometry against a grammar by hierarchical reduction.

Given an input geometry and a grammar, this recognizes the geometry *with* the grammar - the
recognition counterpart of learning. At each step it finds occurrences of some rule's right-hand
side pattern (matched by geometric canonical key), replaces a non-overlapping set of them with the
rule's left-hand-side node, and records the step. The ordered list of reductions is the
**derivation** (the parse); replaying it in reverse (``reconstruct``) regenerates the geometry.

This is exactly like parsing a string with a grammar and then regenerating it from the parse tree:
the grammar's rule shapes drive the analysis, and the derivation drives generation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .detection import detect_isogroups
from .grammar import Grammar
from .graph import GeometricGraph
from .isogroup import Occurrence
from .isomorphism import DEFAULT_QUANT, canonical_form
from .selection import non_overlapping_subset

_NODE_BASE = 10_000_000  # placeholder-node ids live here, clear of input vertex ids


@dataclass
class ReducedOccurrence:
    """One subgraph that was reduced to a node (records enough to restore it exactly)."""

    vertices: list[int]
    positions: dict[int, list[float]]
    internal_edges: list[tuple[int, int]]
    boundary: list[tuple[int, int]]   # (subgraph_vertex_id, external_neighbour_id)
    node_id: int
    node_position: list[float]


@dataclass
class ParseStep:
    rule_id: int
    symbol: str
    level: int
    order: int
    occurrences: list[ReducedOccurrence]
    vertices_before: int
    vertices_after: int
    pre_graph: GeometricGraph | None = None  # snapshot before this step (for visualization)


@dataclass
class ParseResult:
    steps: list[ParseStep]
    reduced: GeometricGraph
    input_vertices: int
    input_edges: int

    @property
    def reductions(self) -> int:
        return sum(len(s.occurrences) for s in self.steps)

    @property
    def recognized(self) -> bool:
        """True if the grammar reduced the geometry at all."""
        return self.reduced.num_vertices < self.input_vertices

    def to_dict(self) -> dict:
        return {
            "input": {"vertices": self.input_vertices, "edges": self.input_edges},
            "reduced": {
                "vertices": self.reduced.num_vertices, "edges": self.reduced.num_edges,
            },
            "steps": [
                {
                    "rule_id": s.rule_id, "symbol": s.symbol, "level": s.level, "order": s.order,
                    "occurrences": len(s.occurrences),
                    "vertices_before": s.vertices_before, "vertices_after": s.vertices_after,
                }
                for s in self.steps
            ],
        }


def _reduce_occurrence(
    g: GeometricGraph, occ: Occurrence, node_id: int, placement: str
) -> ReducedOccurrence:
    occ_set = set(occ)
    positions = {v: g.position(v).tolist() for v in occ_set}
    internal: list[tuple[int, int]] = []
    boundary: list[tuple[int, int]] = []
    external: set[int] = set()
    for v in sorted(occ_set):
        for nb in sorted(g.neighbors(v)):
            if nb in occ_set:
                if v < nb:
                    internal.append((v, nb))
            else:
                boundary.append((v, nb))
                external.add(nb)

    if placement == "centroid":
        pos = g.positions(sorted(occ_set)).mean(axis=0)
    else:  # "existing": the most-connected vertex (paper Fig. 10)
        anchor = max(sorted(occ_set), key=lambda v: g.degree(v))
        pos = g.position(anchor)

    for v in occ_set:
        g.remove_vertex(v)
    g.add_vertex(node_id, pos)
    for x in sorted(external):
        if g.has_vertex(x):
            g.add_edge(node_id, x)

    return ReducedOccurrence(
        vertices=sorted(occ_set), positions=positions, internal_edges=internal,
        boundary=boundary, node_id=node_id, node_position=list(map(float, pos)),
    )


def parse(
    graph: GeometricGraph,
    grammar: Grammar,
    *,
    placement: str = "centroid",
    keep_snapshots: bool = False,
    max_steps: int = 100_000,
    quant: float = DEFAULT_QUANT,
) -> ParseResult:
    """Reduce ``graph`` using ``grammar``'s rules, recording the derivation."""
    g = graph.copy()
    rule_key = {r.id: canonical_form(r.rhs, quant=quant).key for r in grammar.rules}
    # apply lower levels (smaller, earlier-learned structure) first, mirroring how it was built
    rules = sorted(grammar.rules, key=lambda r: (r.level, r.rhs.num_vertices))
    max_order = max((r.rhs.num_vertices for r in grammar.rules), default=2)

    steps: list[ParseStep] = []
    node_counter = 0
    while len(steps) < max_steps:
        isos = detect_isogroups(
            g, max_order=max_order, min_frequency=1, frequency_cut=0.0, quant=quant
        )
        by_key = {iso.key: iso for iso in isos}

        applied = False
        for rule in rules:
            iso = by_key.get(rule_key[rule.id])
            if iso is None:
                continue
            cover = non_overlapping_subset(iso.occurrences)
            if not cover:
                continue
            snapshot = g.copy() if keep_snapshots else None
            before = g.num_vertices
            reduced = []
            for occ in cover:
                node_id = _NODE_BASE + node_counter
                node_counter += 1
                reduced.append(_reduce_occurrence(g, occ, node_id, placement))
            steps.append(ParseStep(
                rule_id=rule.id, symbol=rule.lhs, level=rule.level, order=rule.rhs.num_vertices,
                occurrences=reduced, vertices_before=before, vertices_after=g.num_vertices,
                pre_graph=snapshot,
            ))
            applied = True
            break
        if not applied:
            break

    return ParseResult(
        steps=steps, reduced=g,
        input_vertices=graph.num_vertices, input_edges=graph.num_edges,
    )


def reconstruct(result: ParseResult) -> GeometricGraph:
    """Replay the derivation in reverse to regenerate the geometry from the reduced axiom.

    Each step is undone in two passes: first remove the step's placeholder nodes and restore every
    occurrence's vertices + internal edges, then add the boundary edges. The two-pass order matters
    because sibling occurrences in one step can be adjacent - their shared edge is recorded by
    whichever reduced first (with stable original ids), so adding edges only after all vertices
    exist recovers every connection exactly.
    """
    g = result.reduced.copy()
    for step in reversed(result.steps):
        for occ in step.occurrences:                       # pass 1a: drop placeholder nodes
            if g.has_vertex(occ.node_id):
                g.remove_vertex(occ.node_id)
        for occ in step.occurrences:                       # pass 1b: restore vertices + internals
            for v, pos in occ.positions.items():
                if not g.has_vertex(v):
                    g.add_vertex(v, pos)
            for u, w in occ.internal_edges:
                g.add_edge(u, w)
        for occ in step.occurrences:                       # pass 2: boundary edges
            for sub_v, x in occ.boundary:
                if g.has_vertex(x):
                    g.add_edge(sub_v, x)
    return g


def format_process(result: ParseResult) -> str:
    """Human-readable derivation: one line per reduction step."""
    lines = ["=== syntax analysis (derivation by reduction) ==="]
    lines.append(
        f"input: {result.input_vertices} vertices, {result.input_edges} edges"
    )
    for i, s in enumerate(result.steps):
        lines.append(
            f"  step {i:>3}: rule {s.rule_id} '{s.symbol}' (order {s.order}, level {s.level}) "
            f"reduced {len(s.occurrences)} occurrence(s); "
            f"{s.vertices_before} -> {s.vertices_after} vertices"
        )
    lines.append(
        f"result: {len(result.steps)} step(s), {result.reductions} reduction(s); "
        f"reduced to {result.reduced.num_vertices} vertices, {result.reduced.num_edges} edges "
        f"({'recognized' if result.recognized else 'no rule matched'})"
    )
    return "\n".join(lines)


def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    from .io import load_json
    from .isomorphism import geometric_iso

    parser = argparse.ArgumentParser(
        description="Parse a geometry against a grammar (syntax analysis by reduction)."
    )
    parser.add_argument("geometry", help="input geometry JSON")
    parser.add_argument("grammar", help="grammar file (*.ggg.json)")
    parser.add_argument("--placement", choices=["centroid", "existing"], default="centroid")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_QUANT,
                        help="similarity tolerance; use the SAME value the grammar was trained at")
    parser.add_argument("--node-size", type=float, default=40.0, help="marker size for step PNGs")
    parser.add_argument("--steps-dir", metavar="DIR", help="write a PNG per step (needs 'viz')")
    parser.add_argument("--record", metavar="JSON", help="write the derivation trace as JSON")
    parser.add_argument("--reconstruct", metavar="PNG", help="regenerate geometry and render it")
    args = parser.parse_args(argv)

    geometry = load_json(args.geometry)
    grammar = Grammar.load_json(args.grammar)
    result = parse(
        geometry, grammar, placement=args.placement, keep_snapshots=bool(args.steps_dir),
        quant=args.tolerance,
    )
    print(format_process(result))

    if args.record:
        Path(args.record).write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(f"wrote {args.record}")

    if args.steps_dir:
        from .viz import save_png
        d = Path(args.steps_dir)
        d.mkdir(parents=True, exist_ok=True)
        for i, s in enumerate(result.steps):
            if s.pre_graph is None:
                continue
            groups = [set(o.vertices) for o in s.occurrences]
            save_png(s.pre_graph, str(d / f"step_{i:03d}.png"), groups=groups,
                     node_size=args.node_size)
        # the axiom is often a single node; draw it large so it is clearly visible
        save_png(result.reduced, str(d / "reduced_axiom.png"), node_size=300.0)
        print(
            f"wrote {len(result.steps)} step image(s) + reduced_axiom.png "
            f"(axiom: {result.reduced.num_vertices} vertex/vertices) to {d}"
        )

    if args.reconstruct:
        rebuilt = reconstruct(result)
        ok = geometric_iso(geometry, rebuilt) if geometry.num_edges else (
            rebuilt.num_vertices == geometry.num_vertices
        )
        from .viz import save_png
        save_png(rebuilt, args.reconstruct, node_size=args.node_size)
        print(
            f"reconstructed {rebuilt.num_vertices} vertices, {rebuilt.num_edges} edges -> "
            f"{args.reconstruct} (matches input: {ok})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
