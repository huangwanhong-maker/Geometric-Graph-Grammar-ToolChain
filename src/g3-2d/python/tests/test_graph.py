import numpy as np
import pytest

from g3_2d.generators import grid_graph
from g3_2d.graph import GeometricGraph


def triangle() -> GeometricGraph:
    g = GeometricGraph()
    g.add_vertex(0, (0, 0))
    g.add_vertex(1, (1, 0))
    g.add_vertex(2, (0, 1))
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 0)
    return g


def test_basic_counts_and_queries():
    g = triangle()
    assert g.num_vertices == 3
    assert g.num_edges == 3
    assert g.vertices() == [0, 1, 2]
    assert g.edges() == [(0, 1), (0, 2), (1, 2)]
    assert g.neighbors(0) == {1, 2}
    assert g.degree(1) == 2
    assert g.has_edge(2, 0) and g.has_edge(0, 2)
    assert np.allclose(g.position(2), [0, 1])


def test_no_loops_and_missing_endpoints():
    g = triangle()
    with pytest.raises(ValueError):
        g.add_edge(0, 0)
    with pytest.raises(KeyError):
        g.add_edge(0, 99)


def test_induced_subgraph_keeps_all_internal_edges():
    # path 0-1-2-3 plus chord 0-2; inducing {0,1,2} must keep edge (0,2)
    g = GeometricGraph()
    for i in range(4):
        g.add_vertex(i, (i, 0))
    for u, v in [(0, 1), (1, 2), (2, 3), (0, 2)]:
        g.add_edge(u, v)
    sub = g.induced_subgraph([0, 1, 2])
    assert sub.num_vertices == 3
    assert set(sub.edges()) == {(0, 1), (0, 2), (1, 2)}


def test_grid_graph_structure():
    g = grid_graph(3, 3)
    assert g.num_vertices == 9
    # 2 rows*3 horizontal + 2 cols*3 vertical = 6 + 6 = 12 edges
    assert g.num_edges == 12
    assert g.degree(4) == 4  # center vertex
    assert g.degree(0) == 2  # corner


def test_copy_is_independent():
    g = triangle()
    h = g.copy()
    h.add_vertex(3, (5, 5))
    assert g.num_vertices == 3 and h.num_vertices == 4
