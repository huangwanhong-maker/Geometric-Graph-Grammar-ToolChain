import numpy as np

from g3_2d.detection import detect_isogroups
from g3_2d.encoder import encode_rule
from g3_2d.generators import grid_graph
from g3_2d.io import load_json
from g3_2d.learn import learn, rewrite
from g3_2d.selection import non_overlapping_subset, select_isogroup


def two_triangles():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[4]
    return load_json(root / "fixtures" / "graphs" / "two_triangles.json")


# -- detection ---------------------------------------------------------------------------------
def test_detect_two_triangles():
    g = two_triangles()
    isos = detect_isogroups(g)
    triangles = [i for i in isos if i.order == 3]
    assert len(triangles) == 1
    assert triangles[0].frequency == 2


def test_detect_grid_finds_unit_square():
    g = grid_graph(4, 4)
    isos = detect_isogroups(g, max_order=4)
    squares = [i for i in isos if i.order == 4 and i.frequency == 9]  # 3x3 = 9 unit squares
    assert squares, "expected to find the 9 unit squares of a 4x4 grid"


# -- selection ---------------------------------------------------------------------------------
def test_non_overlapping_subset():
    a = frozenset({0, 1, 2})
    b = frozenset({3, 4, 5})   # disjoint from a
    c = frozenset({2, 6, 7})   # overlaps a (shares 2)
    subset = non_overlapping_subset([a, b, c])
    assert frozenset(a) in subset and frozenset(b) in subset
    assert len(subset) == 2  # a and b; c conflicts with a


def test_cover_is_disjoint_even_above_clique_cap():
    import itertools

    from g3_2d.selection import best_rule
    g = grid_graph(5, 5)  # produces isogroups with > 60 occurrences -> greedy fallback path
    iso, cover = best_rule(detect_isogroups(g, max_order=4))
    for a, b in itertools.combinations(cover, 2):
        assert a.isdisjoint(b), "non-overlapping cover must be pairwise vertex-disjoint"


def test_select_isogroup_prefers_largest():
    g = two_triangles()
    best = select_isogroup(detect_isogroups(g))
    assert best is not None and best.order == 3  # the triangle, larger than the edge isogroup


# -- encoder -----------------------------------------------------------------------------------
def test_encode_rule_occurrences_reproduce_world_positions():
    g = two_triangles()
    iso = next(i for i in detect_isogroups(g) if i.order == 3)
    rule = encode_rule(g, iso, list(iso.occurrences))
    assert rule.rhs.num_vertices == 3 and rule.rhs.num_edges == 3
    assert len(rule.occurrences) == 2
    # each occurrence's transform must map RHS-local coords back to the matched world vertices
    for occ in rule.occurrences:
        for i, world_id in occ.vertices.items():
            placed = occ.transform.apply(rule.rhs.position(i))
            assert np.allclose(placed, g.position(world_id), atol=1e-9)


# -- rewrite -----------------------------------------------------------------------------------
def test_rewrite_replaces_subgraphs_with_nodes():
    g = two_triangles()
    a = frozenset({0, 1, 2})
    b = frozenset({3, 4, 5})
    reduced = rewrite(g, [a, b], [np.array([0.0, 0.0]), np.array([10.0, 0.0])])
    # two triangles (disjoint, no inter-edges) collapse to two isolated nodes
    assert reduced.num_vertices == 2
    assert reduced.num_edges == 0


# -- full learn --------------------------------------------------------------------------------
def test_learn_two_triangles_yields_one_rule():
    g = two_triangles()
    grammar = learn(g)
    assert len(grammar.rules) == 1
    r = grammar.rules[0]
    assert r.rhs.num_vertices == 3
    assert r.frequency == 2
    assert len(r.occurrences) == 2
    # axiom is the compressed graph: the two triangles became two nodes
    assert grammar.axiom is not None and grammar.axiom.num_vertices == 2


def test_learn_grid_compresses():
    g = grid_graph(4, 4)
    grammar = learn(g, max_levels=2, max_order=4)
    assert len(grammar.rules) >= 1
    # compression: the axiom has fewer vertices than the input
    assert grammar.axiom is not None
    assert grammar.axiom.num_vertices < g.num_vertices
