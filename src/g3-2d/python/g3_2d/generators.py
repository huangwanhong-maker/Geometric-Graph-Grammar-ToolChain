"""Synthetic geometric-graph generators with known ground truth.

Used for development and tests: a regular grid is the paper's own noise-robustness benchmark
(Fig. 14), and gives us patterns whose repetition counts we can assert exactly.
"""

from __future__ import annotations

import numpy as np

from .graph import GeometricGraph


def grid_graph(rows: int, cols: int, spacing: float = 1.0) -> GeometricGraph:
    """A ``rows x cols`` 4-connected lattice. Vertex id = ``r * cols + c``; positions on a grid."""
    g = GeometricGraph()
    for r in range(rows):
        for c in range(cols):
            g.add_vertex(r * cols + c, (c * spacing, r * spacing))
    for r in range(rows):
        for c in range(cols):
            v = r * cols + c
            if c + 1 < cols:
                g.add_edge(v, v + 1)
            if r + 1 < rows:
                g.add_edge(v, v + cols)
    return g


def jitter(g: GeometricGraph, sigma: float, rng: np.random.Generator) -> GeometricGraph:
    """Copy ``g`` with each vertex position perturbed by Gaussian noise (paper Fig. 14)."""
    out = GeometricGraph()
    for v in g.vertices():
        out.add_vertex(v, g.position(v) + rng.normal(0.0, sigma, size=2))
    for u, v in g.edges():
        out.add_edge(u, v)
    return out
