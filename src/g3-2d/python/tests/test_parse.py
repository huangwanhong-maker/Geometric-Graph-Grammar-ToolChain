from g3_2d.examples import sierpinski
from g3_2d.forward import generate
from g3_2d.generators import grid_graph
from g3_2d.isomorphism import geometric_iso
from g3_2d.learn import learn
from g3_2d.parse import parse, reconstruct


def test_parse_reduces_grid_and_reconstructs_exactly():
    g = grid_graph(4, 4)
    grammar = learn(g, max_order=4, prefer="dense")
    result = parse(g, grammar)
    assert result.recognized
    assert result.reduced.num_vertices < g.num_vertices
    rebuilt = reconstruct(result)
    assert geometric_iso(rebuilt, g)  # exact round-trip


def test_parse_fractal_roundtrip():
    g = generate(sierpinski(), 3)  # 42 vertices, 81 edges
    grammar = learn(g, max_order=3, prefer="dense")
    result = parse(g, grammar)
    assert result.recognized
    rebuilt = reconstruct(result)
    assert (rebuilt.num_vertices, rebuilt.num_edges) == (g.num_vertices, g.num_edges)
    assert geometric_iso(rebuilt, g)


def test_parse_derivation_is_recorded():
    g = grid_graph(4, 4)
    grammar = learn(g, max_order=4, prefer="dense")
    result = parse(g, grammar)
    d = result.to_dict()
    assert d["input"]["vertices"] == 16
    assert len(d["steps"]) == len(result.steps) >= 1
    # every step names a real rule and reduces the vertex count
    for s in result.steps:
        assert s.vertices_after < s.vertices_before
