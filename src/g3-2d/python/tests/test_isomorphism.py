import numpy as np

from g3_2d.geometry import Similarity
from g3_2d.graph import GeometricGraph
from g3_2d.isomorphism import canonical_key, geometric_iso


def scalene() -> GeometricGraph:
    """An asymmetric (chiral) triangle so reflection is distinguishable."""
    g = GeometricGraph()
    g.add_vertex(0, (0.0, 0.0))
    g.add_vertex(1, (3.0, 0.0))
    g.add_vertex(2, (1.0, 2.0))
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 0)
    return g


def transformed(g: GeometricGraph, T: Similarity, relabel: dict[int, int] | None = None):
    out = GeometricGraph()
    relabel = relabel or {v: v for v in g.vertices()}
    for v in g.vertices():
        out.add_vertex(relabel[v], T.apply(g.position(v)))
    for u, v in g.edges():
        out.add_edge(relabel[u], relabel[v])
    return out


def test_similarity_invariance():
    g = scalene()
    T = Similarity.from_components(scale=2.3, angle=1.1, tx=-4.0, ty=7.0)
    assert geometric_iso(g, transformed(g, T))


def test_relabel_invariance():
    g = scalene()
    relabel = {0: 10, 1: 20, 2: 30}
    assert geometric_iso(g, transformed(g, Similarity.identity(), relabel))


def test_reflection_is_not_isomorphic():
    g = scalene()
    mirror = Similarity(np.array([[1.0, 0.0], [0.0, -1.0]]), np.zeros(2))
    assert not geometric_iso(g, transformed(g, mirror))


def test_different_shapes_differ():
    g = scalene()
    h = GeometricGraph()
    h.add_vertex(0, (0.0, 0.0))
    h.add_vertex(1, (3.0, 0.0))
    h.add_vertex(2, (1.5, 2.0))  # isoceles, different shape
    h.add_edge(0, 1)
    h.add_edge(1, 2)
    h.add_edge(2, 0)
    assert not geometric_iso(g, h)


def test_canonical_key_is_stable():
    g = scalene()
    assert canonical_key(g) == canonical_key(g.copy())
