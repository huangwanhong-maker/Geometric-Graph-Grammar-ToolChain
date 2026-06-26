"""Graph grammar encoder (paper Section 6).

Turns a selected isogroup and a set of (non-overlapping) occurrences into one production rule
``q -> S / B``:

* **RHS** ``S`` - the canonical subgraph, in canonical-local coordinates (vertices relabelled
  ``0..n-1`` by canonical order so every occurrence aligns to the same template).
* **Embedding** ``B`` - per RHS vertex, a local coordinate frame ``T_i`` (oriented toward its
  lowest-indexed neighbour, paper's edge-direction convention) and the relative positions ``p_ij``
  of the external neighbours that vertex reconnects to, taken from a representative occurrence.
* **Occurrences** - for every occurrence, the similarity mapping RHS-local coordinates to world
  coordinates, the RHS-local -> input-graph vertex map, and the chosen world position of ``q``.

Left-hand-side node placement (paper Fig. 10): ``"existing"`` puts ``q`` at the occurrence's
highest-degree (most important) vertex - the paper's recommendation to avoid star artifacts;
``"centroid"`` puts it at the occurrence centroid.
"""

from __future__ import annotations

import numpy as np

from .geometry import Similarity
from .grammar import EmbeddingEntry, Rule
from .grammar import Occurrence as RuleOccurrence
from .graph import GeometricGraph
from .isogroup import Isogroup, Occurrence
from .isomorphism import DEFAULT_QUANT, canonical_form


def _local_frame(rhs: GeometricGraph, i: int) -> Similarity:
    """Frame mapping canonical-local coords into vertex ``i``'s local system (paper's T_i).

    Origin at ``i``, +x axis toward its lowest-indexed neighbour, unit scale (distance-preserving).
    """
    p = rhs.position(i)
    neighbors = sorted(rhs.neighbors(i))
    if neighbors:
        d = rhs.position(neighbors[0]) - p
        angle = float(np.arctan2(d[1], d[0]))
    else:
        angle = 0.0
    rot = Similarity.from_components(angle=-angle)
    translate = Similarity(np.eye(2), -p)
    return rot.compose(translate)


def _node_position(graph: GeometricGraph, occ: Occurrence, placement: str) -> np.ndarray:
    if placement == "centroid":
        return graph.positions(sorted(occ)).mean(axis=0)
    if placement == "existing":
        # highest-degree (most important) vertex, tie-break lowest id
        w = max(sorted(occ), key=lambda v: graph.degree(v))
        return graph.position(w)
    raise ValueError(f"unknown node placement: {placement!r}")


def encode_rule(
    graph: GeometricGraph,
    iso: Isogroup,
    occurrences: list[Occurrence],
    *,
    rule_id: int = 0,
    level: int = 0,
    symbol: str | None = None,
    placement: str = "existing",
    quant: float = DEFAULT_QUANT,
) -> Rule:
    """Encode one isogroup into a production rule ``q -> S / B`` with recorded occurrences."""
    if not occurrences:
        raise ValueError("cannot encode a rule with no occurrences")

    # --- RHS S: canonical template from a representative occurrence ---------------------------
    rep = occurrences[0]
    sub_rep = graph.induced_subgraph(rep)
    form_rep = canonical_form(sub_rep, quant=quant)
    order_rep = form_rep.order                       # RHS-local i -> world id (representative)
    local_index = {w: i for i, w in enumerate(order_rep)}

    rhs = GeometricGraph()
    local_coords = form_rep.transform.apply(sub_rep.positions(list(order_rep)))
    for i, _w in enumerate(order_rep):
        rhs.add_vertex(i, local_coords[i])
    for u, v in sub_rep.edges():
        rhs.add_edge(local_index[u], local_index[v])

    # --- Embedding B: local frames + external connections (from the representative) -----------
    embedding: list[EmbeddingEntry] = []
    for i, w in enumerate(order_rep):
        frame = _local_frame(rhs, i)
        connections = []
        for x in sorted(graph.neighbors(w) - set(rep)):
            x_local = form_rep.transform.apply(graph.position(x))
            connections.append(frame.apply(x_local))
        embedding.append(EmbeddingEntry(vertex=i, transform=frame, connections=connections))

    # --- Occurrences: world placement of every instance ---------------------------------------
    rule_occurrences: list[RuleOccurrence] = []
    for occ in occurrences:
        form = canonical_form(graph.induced_subgraph(occ), quant=quant)
        vmap = {i: form.order[i] for i in range(len(form.order))}
        rule_occurrences.append(
            RuleOccurrence(
                transform=form.transform.inverse(),   # RHS-local -> world
                vertices=vmap,
                node_position=_node_position(graph, occ, placement),
            )
        )

    return Rule(
        id=rule_id,
        lhs=symbol or f"R{rule_id}",
        rhs=rhs,
        embedding=embedding,
        level=level,
        frequency=iso.frequency,
        occurrences=rule_occurrences,
    )
