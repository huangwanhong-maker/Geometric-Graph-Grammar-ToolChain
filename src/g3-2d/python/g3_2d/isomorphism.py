"""Geometric isomorphism and canonical form (paper Section 3.2).

Two geometric graphs are *geometrically isomorphic* when there is a graph isomorphism plus a
transformation aligning their coordinates. We restrict the transformation to **similarity**
(rotation + uniform scale + translation, orientation-preserving) - this matches the paper's
examples and keeps "same shape" meaningful (full affine would collapse almost everything together).

Strategy: compute a deterministic, quantized **canonical form**. For every directed edge ``(a, b)``
we pin ``a -> (0,0)`` and ``b -> (1,0)`` (the unique proper similarity, ``similarity_from_edge``),
quantize all vertex coordinates, and read off a labelling-invariant token plus a canonical vertex
order. The canonical form is the one whose token is lexicographically smallest over all directed
edges. Isomorphic graphs (within the quantization tolerance) produce identical tokens, AND their
canonical orders align corresponding vertices - which is what the encoder uses to map one
occurrence's vertices onto another's. This is the same quantization philosophy the paper uses for
its polar expansion grid, and it gives the determinism the cross-implementation oracle needs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import Similarity, similarity_from_edge
from .graph import GeometricGraph

# A canonical key: (sorted quantized coordinates, sorted edges over canonical indices).
CanonicalKey = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

DEFAULT_QUANT = 0.05  # quantization step in units where the frame edge has length 1


@dataclass(frozen=True)
class CanonicalForm:
    """The canonical view of a geometric graph under orientation-preserving similarity."""

    key: CanonicalKey
    transform: Similarity   # maps world coordinates -> canonical-local coordinates
    order: tuple[int, ...]  # original vertex ids in canonical order (RHS-local i -> order[i])


def _frame_form(g: GeometricGraph, a: int, b: int, quant: float) -> CanonicalForm | None:
    """Canonical form of ``g`` viewed in the frame that pins directed edge ``(a, b)``."""
    try:
        T = similarity_from_edge(g.position(a), g.position(b))
    except ValueError:
        return None
    verts = g.vertices()
    coords = T.apply(g.positions(verts))
    q = np.round(coords / quant).astype(int)

    # canonical vertex order: sort by quantized coordinate, then by degree for tie-breaks
    idx = sorted(
        range(len(verts)),
        key=lambda i: (int(q[i, 0]), int(q[i, 1]), g.degree(verts[i])),
    )
    pos_of = {verts[old]: new for new, old in enumerate(idx)}
    qcoords = tuple((int(q[i, 0]), int(q[i, 1])) for i in idx)
    edges = tuple(sorted(tuple(sorted((pos_of[u], pos_of[v]))) for u, v in g.edges()))
    order = tuple(verts[i] for i in idx)
    return CanonicalForm(key=(qcoords, edges), transform=T, order=order)


def canonical_form(g: GeometricGraph, *, quant: float = DEFAULT_QUANT) -> CanonicalForm:
    """Deterministic canonical form of ``g`` under orientation-preserving similarity.

    Requires at least one edge (every pattern produced by edge-seeded expansion has one).
    """
    best: CanonicalForm | None = None
    for u, v in g.edges():
        for a, b in ((u, v), (v, u)):
            form = _frame_form(g, a, b, quant)
            if form is not None and (best is None or form.key < best.key):
                best = form
    if best is None:
        raise ValueError("canonical_form requires a graph with at least one edge")
    return best


def canonical_key(g: GeometricGraph, *, quant: float = DEFAULT_QUANT) -> CanonicalKey:
    """Deterministic canonical key of ``g`` (the token only)."""
    return canonical_form(g, quant=quant).key


def geometric_iso(
    g1: GeometricGraph, g2: GeometricGraph, *, quant: float = DEFAULT_QUANT
) -> bool:
    """True iff ``g1`` and ``g2`` are geometrically isomorphic under similarity (within quant)."""
    if g1.num_vertices != g2.num_vertices or g1.num_edges != g2.num_edges:
        return False
    return canonical_key(g1, quant=quant) == canonical_key(g2, quant=quant)
