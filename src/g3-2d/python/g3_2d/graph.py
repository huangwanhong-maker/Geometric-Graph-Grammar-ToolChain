"""The geometric graph data model (paper Section 3.1).

A simple, undirected graph whose every vertex carries a 2D position. Vertices are identified by
hashable ids (ints by convention). The model is intentionally minimal and explicit so the C++ port
can mirror it; we do not depend on a graph library.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

import numpy as np

Vertex = int
Edge = tuple[Vertex, Vertex]


def _norm_edge(u: Vertex, v: Vertex) -> Edge:
    return (u, v) if u <= v else (v, u)


class GeometricGraph:
    """An undirected simple geometric graph ``G = (V, E)`` with a position ``c(v)`` per vertex."""

    def __init__(self) -> None:
        self._adj: dict[Vertex, set[Vertex]] = {}
        self._pos: dict[Vertex, np.ndarray] = {}

    # -- construction --------------------------------------------------------------------------
    def add_vertex(self, v: Vertex, position: Iterable[float]) -> None:
        pos = np.asarray(position, dtype=float).reshape(2)
        if v in self._adj and not np.array_equal(self._pos[v], pos):
            raise ValueError(f"vertex {v} already exists with a different position")
        self._adj.setdefault(v, set())
        self._pos[v] = pos

    def add_edge(self, u: Vertex, v: Vertex) -> None:
        if u == v:
            raise ValueError("loops are not allowed in a simple graph")
        if u not in self._adj or v not in self._adj:
            raise KeyError("both endpoints must be added as vertices first")
        self._adj[u].add(v)
        self._adj[v].add(u)

    def remove_vertex(self, v: Vertex) -> None:
        """Remove ``v`` and all its incident edges."""
        for u in self._adj.pop(v):
            self._adj[u].discard(v)
        self._pos.pop(v, None)

    def fresh_vertex_id(self) -> Vertex:
        """An integer id not currently in use (max existing id + 1, or 0 if empty)."""
        return max(self._adj, default=-1) + 1

    # -- queries -------------------------------------------------------------------------------
    def has_vertex(self, v: Vertex) -> bool:
        return v in self._adj

    def has_edge(self, u: Vertex, v: Vertex) -> bool:
        return v in self._adj.get(u, ())

    def neighbors(self, v: Vertex) -> set[Vertex]:
        return set(self._adj[v])

    def degree(self, v: Vertex) -> int:
        return len(self._adj[v])

    def position(self, v: Vertex) -> np.ndarray:
        return self._pos[v]

    def positions(self, order: Iterable[Vertex]) -> np.ndarray:
        return np.array([self._pos[v] for v in order], dtype=float)

    @property
    def num_vertices(self) -> int:
        return len(self._adj)

    @property
    def num_edges(self) -> int:
        return sum(len(ns) for ns in self._adj.values()) // 2

    def vertices(self) -> list[Vertex]:
        """Vertices in sorted order (deterministic)."""
        return sorted(self._adj)

    def edges(self) -> list[Edge]:
        """Edges as sorted, normalized ``(min, max)`` tuples, in sorted order (deterministic)."""
        seen: set[Edge] = set()
        for u, ns in self._adj.items():
            for v in ns:
                seen.add(_norm_edge(u, v))
        return sorted(seen)

    def __iter__(self) -> Iterator[Vertex]:
        return iter(self.vertices())

    # -- derived graphs ------------------------------------------------------------------------
    def induced_subgraph(self, vertices: Iterable[Vertex]) -> GeometricGraph:
        """The induced subgraph on ``vertices``: keeps ALL edges with both endpoints inside.

        Vertex ids and positions are preserved (paper Section 3.1, induced subgraph).
        """
        vset = set(vertices)
        missing = vset - self._adj.keys()
        if missing:
            raise KeyError(f"vertices not in graph: {sorted(missing)}")
        sub = GeometricGraph()
        for v in vset:
            sub.add_vertex(v, self._pos[v])
        for u in vset:
            for v in self._adj[u] & vset:
                if u < v:
                    sub.add_edge(u, v)
        return sub

    def copy(self) -> GeometricGraph:
        g = GeometricGraph()
        for v, pos in self._pos.items():
            g.add_vertex(v, pos)
        for u, v in self.edges():
            g.add_edge(u, v)
        return g

    def __repr__(self) -> str:
        return f"GeometricGraph(|V|={self.num_vertices}, |E|={self.num_edges})"
