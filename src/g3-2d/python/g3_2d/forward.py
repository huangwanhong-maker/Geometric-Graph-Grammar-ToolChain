"""Forward generation: applying a grammar to grow a geometric graph (paper Section 3, Fig. 12).

This is the generative counterpart of learning. A structure is a list of *modules* - each a symbol
plus a local coordinate frame (a similarity transform), exactly the turtle idea of L-systems
generalized to graphs. A production replaces a symbol with child modules whose frames are the
parent frame **composed** with per-child transforms; composing similarities across levels multiplies
the scale, which is what produces self-similar (fractal) structures such as the Sierpinski triangle.

After a fixed number of parallel derivation steps, each surviving module is rendered using its
symbol's *terminal shape* (a small graph in local coordinates); coincident vertices are merged so
the pieces connect into one geometric graph.

This module uses a small ``ForwardGrammar`` spec aimed at generation; the embedding transforms of a
*learned* ``Grammar`` are the same kind of per-child similarity, so the two can be unified later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .geometry import Similarity
from .graph import GeometricGraph

Module = tuple[str, Similarity]  # (symbol, frame mapping local coords -> world)


@dataclass
class Production:
    """A forward production: ``symbol`` expands into child modules (child symbol + transform)."""

    symbol: str
    children: list[tuple[str, Similarity]]


@dataclass
class ForwardGrammar:
    """Axiom modules + productions + per-symbol terminal shapes (local geometry drawn at leaves)."""

    axiom: list[Module]
    productions: dict[str, Production] = field(default_factory=dict)
    terminals: dict[str, GeometricGraph] = field(default_factory=dict)


def derive(grammar: ForwardGrammar, iterations: int) -> list[Module]:
    """Apply productions ``iterations`` times in parallel, returning the final modules."""
    modules = list(grammar.axiom)
    for _ in range(iterations):
        nxt: list[Module] = []
        for sym, frame in modules:
            prod = grammar.productions.get(sym)
            if prod is None:
                nxt.append((sym, frame))  # no production: carry through unchanged
            else:
                for csym, t in prod.children:
                    nxt.append((csym, frame.compose(t)))
        modules = nxt
    return modules


def render(
    grammar: ForwardGrammar, modules: list[Module], *, merge_tol: float = 1e-6
) -> GeometricGraph:
    """Render modules into one geometric graph, merging vertices closer than ``merge_tol``."""
    g = GeometricGraph()
    index: dict[tuple[int, int], int] = {}  # quantized position -> vertex id
    next_id = 0

    def vertex_at(p: np.ndarray) -> int:
        nonlocal next_id
        key = (round(float(p[0]) / merge_tol), round(float(p[1]) / merge_tol))
        if key not in index:
            index[key] = next_id
            g.add_vertex(next_id, p)
            next_id += 1
        return index[key]

    for sym, frame in modules:
        shape = grammar.terminals.get(sym)
        if shape is None:
            continue
        local_ids = {v: vertex_at(frame.apply(shape.position(v))) for v in shape.vertices()}
        for u, v in shape.edges():
            a, b = local_ids[u], local_ids[v]
            if a != b and not g.has_edge(a, b):
                g.add_edge(a, b)
    return g


def generate(
    grammar: ForwardGrammar, iterations: int, *, merge_tol: float = 1e-6
) -> GeometricGraph:
    """Derive ``iterations`` steps and render the result (forward modeling end to end)."""
    return render(grammar, derive(grammar, iterations), merge_tol=merge_tol)
