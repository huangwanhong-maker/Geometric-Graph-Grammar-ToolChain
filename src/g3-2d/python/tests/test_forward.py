from g3_2d.examples import sierpinski
from g3_2d.forward import generate
from g3_2d.learn import learn


def test_sierpinski_counts_grow_as_fractal():
    # depth 0: a single triangle
    g0 = generate(sierpinski(), 0)
    assert (g0.num_vertices, g0.num_edges) == (3, 3)
    # depth 1: three corner triangles sharing the edge midpoints -> 6 vertices, 9 edges
    g1 = generate(sierpinski(), 1)
    assert (g1.num_vertices, g1.num_edges) == (6, 9)
    # depth 2: nine triangles -> (3^3+3)/2 = 15 vertices, 27 edges
    g2 = generate(sierpinski(), 2)
    assert (g2.num_vertices, g2.num_edges) == (15, 27)


def test_sierpinski_triangle_count_is_three_to_the_n():
    # every leaf module renders one small triangle -> 3 edges each, no shared edges
    for n in range(5):
        g = generate(sierpinski(), n)
        assert g.num_edges == 3 * (3**n)


def test_roundtrip_fractal_induces_triangle_hierarchy():
    # forward-generate a Sierpinski graph, then induce a grammar back from it
    g = generate(sierpinski(), 3)  # 27 small triangles

    # prefer="dense" should encode the fractal's natural unit: a closed triangle (3v, 3e)
    dense = learn(g, max_order=3, prefer="dense")
    assert dense.rules[0].rhs.num_vertices == 3
    assert dense.rules[0].rhs.num_edges == 3            # a 3-cycle, not a path
    assert len(dense.rules) >= 3                        # multi-level (hierarchical) encoding

    # prefer="gain" picks 3-vertex paths (2 edges) instead - more disjoint copies
    gain = learn(g, max_order=3, prefer="gain")
    assert gain.rules[0].rhs.num_edges == 2
