"""Vertex expansion via two polar grids (paper Section 5.1, Fig. 6).

Given an isogroup with pattern ``F`` and all its occurrences, we extend ``F`` by one vertex. Every
occurrence is normalized into its canonical frame so all occurrences are aligned (same scale and
rotation). Candidate vertices (neighbours of ``F`` not yet in it) are dropped into two discrete
polar grids centred on the pattern:

* a **count** grid - how many occurrences have a candidate in each cell (the repetition frequency);
* an **area** grid - the convex-hull area added by placing a vertex at the cell centre.

Each cell is scored ``frequency * added_area`` (paper's two heuristics combined). Every cell that
repeats at least ``min_frequency`` times spawns a candidate child isogroup, built from the actual
candidate vertices that landed in that cell. Generating from all frequent cells (rather than only
the single best) reproduces Fig. 7's "expand to all possible cases"; detection then merges
isomorphic children and prunes by frequency.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import PolarGrid, convex_hull_area
from .graph import GeometricGraph
from .isogroup import Isogroup, Occurrence
from .isomorphism import DEFAULT_QUANT, canonical_form


@dataclass(frozen=True)
class ExpansionParams:
    grid: PolarGrid = PolarGrid(n_angle=10, n_dist=12, max_radius=3.0)
    min_frequency: int = 2
    quant: float = DEFAULT_QUANT


def _candidate_vertices(graph: GeometricGraph, occ: Occurrence) -> set[int]:
    """Vertices adjacent to the occurrence but not inside it."""
    cand: set[int] = set()
    for v in occ:
        cand |= graph.neighbors(v)
    return cand - set(occ)


def expand_isogroup(
    graph: GeometricGraph, iso: Isogroup, params: ExpansionParams | None = None
) -> list[Isogroup]:
    """Expand one isogroup by a vertex, returning candidate child isogroups (order + 1)."""
    params = params or ExpansionParams()
    grid = params.grid

    # cell -> {occurrence (frozenset) : chosen candidate vertex} (one candidate per occ per cell)
    cell_members: dict[tuple[int, int], dict[Occurrence, int]] = {}

    for occ in iso.occurrences:
        form = canonical_form(graph.induced_subgraph(occ), quant=params.quant)
        T = form.transform  # world -> canonical-local
        for c in sorted(_candidate_vertices(graph, occ)):
            cell = grid.cell_of(T.apply(graph.position(c)))
            if cell is None:
                continue
            members = cell_members.setdefault(cell, {})
            # one candidate per occurrence per cell: keep the lowest-id (deterministic)
            if occ not in members or c < members[occ]:
                members[occ] = c

    # base hull area of the canonical pattern (for the added-area heuristic)
    base_form = canonical_form(iso.pattern, quant=params.quant)
    base_pts = base_form.transform.apply(iso.pattern.positions(iso.pattern.vertices()))
    base_area = convex_hull_area(base_pts)

    # build scored candidate children from frequent cells
    scored: list[tuple[float, tuple[int, int], dict[Occurrence, int]]] = []
    for cell, members in cell_members.items():
        if len(members) < params.min_frequency:
            continue
        added = convex_hull_area(np.vstack([base_pts, grid.cell_center(*cell)])) - base_area
        score = len(members) * max(added, 0.0)
        scored.append((score, cell, members))

    # deterministic order: highest score first, then cell index
    scored.sort(key=lambda t: (-t[0], t[1]))

    children: dict = {}  # canonical key -> Isogroup
    for _score, _cell, members in scored:
        for occ, cand in members.items():
            child_occ: Occurrence = frozenset(occ | {cand})
            sub = graph.induced_subgraph(child_occ)
            key = canonical_form(sub, quant=params.quant).key
            grp = children.get(key)
            if grp is None:
                children[key] = Isogroup(key=key, pattern=sub, occurrences=[child_occ])
            elif child_occ not in grp.occurrences:
                grp.occurrences.append(child_occ)
    return list(children.values())
