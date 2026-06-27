"""Isogroup detection: the bottom-up expansion loop (paper Section 5.1, Fig. 7).

Start from a seed isogroup (by default the single isogroup of all edges, "Order 2") and repeatedly
apply vertex expansion. After each round, children discovered from different parents are merged by
canonical key (isomorphism-based removal), then low-frequency isogroups are pruned
(frequency-based removal). The loop stops at ``max_order`` or when no child repeats often enough.
"""

from __future__ import annotations

from .expansion import ExpansionParams, expand_isogroup
from .graph import GeometricGraph
from .isogroup import Isogroup, Occurrence
from .isomorphism import DEFAULT_QUANT, canonical_form


def _seed_from_edges(graph: GeometricGraph, quant: float) -> Isogroup | None:
    """The Order-2 isogroup: every edge is an occurrence (all edges are isomorphic)."""
    edges = graph.edges()
    if not edges:
        return None
    occurrences: list[Occurrence] = [frozenset(e) for e in edges]
    pattern = graph.induced_subgraph(edges[0])
    return Isogroup(
        key=canonical_form(pattern, quant=quant).key, pattern=pattern, occurrences=occurrences
    )


def _merge_by_key(groups: list[Isogroup]) -> list[Isogroup]:
    merged: dict = {}
    for g in groups:
        cur = merged.get(g.key)
        if cur is None:
            merged[g.key] = Isogroup(key=g.key, pattern=g.pattern, occurrences=list(g.occurrences))
        else:
            seen = set(cur.occurrences)
            for occ in g.occurrences:
                if occ not in seen:
                    cur.occurrences.append(occ)
                    seen.add(occ)
    return list(merged.values())


def _frequency_cut(groups: list[Isogroup], cut: float) -> list[Isogroup]:
    """Discard the least-frequent fraction ``cut`` of isogroups (frequency-based removal)."""
    if cut <= 0.0 or len(groups) <= 1:
        return groups
    ordered = sorted(groups, key=lambda g: (-g.frequency, -g.order, g.key))
    keep = max(1, int(round(len(ordered) * (1.0 - cut))))
    return ordered[:keep]


def detect_isogroups(
    graph: GeometricGraph,
    *,
    max_order: int | None = None,
    min_frequency: int = 2,
    frequency_cut: float = 0.0,
    quant: float = DEFAULT_QUANT,
    params: ExpansionParams | None = None,
    seed: Isogroup | None = None,
) -> list[Isogroup]:
    """Detect repeated isogroups of every order from 2 up to ``max_order``.

    ``frequency_cut`` is the fraction of least-frequent isogroups discarded each round (the paper
    uses ~0.8 for speed; default 0.0 = full analysis = ground truth). ``min_frequency`` is the
    minimum repetition count to keep a pattern. ``quant`` is the geometric similarity tolerance (the
    quantization step in units where a reference edge has length 1; larger = looser matching, so
    approximately-similar structures - e.g. organic settlements - are grouped together). With
    ``seed`` you can start from a user-defined subgraph instead of a single edge.
    """
    params = params or ExpansionParams(min_frequency=min_frequency, quant=quant)
    start = seed or _seed_from_edges(graph, params.quant)
    if start is None or start.frequency < min_frequency:
        return []

    all_groups: list[Isogroup] = [start]
    current: list[Isogroup] = [start]

    while max_order is None or current[0].order < max_order:
        produced: list[Isogroup] = []
        for iso in current:
            if iso.frequency >= min_frequency:
                produced.extend(expand_isogroup(graph, iso, params))

        children = [g for g in _merge_by_key(produced) if g.frequency >= min_frequency]
        children = _frequency_cut(children, frequency_cut)
        if not children:
            break

        all_groups.extend(children)
        current = children

    return all_groups
