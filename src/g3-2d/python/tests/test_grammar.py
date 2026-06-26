import numpy as np

from g3_2d.geometry import Similarity
from g3_2d.grammar import EmbeddingEntry, Grammar, Occurrence, Rule
from g3_2d.graph import GeometricGraph


def sample_rule() -> Rule:
    # RHS subgraph S: a triangle a,b,c
    s = GeometricGraph()
    s.add_vertex(0, (0.0, 0.0))
    s.add_vertex(1, (1.0, 0.0))
    s.add_vertex(2, (0.0, 1.0))
    s.add_edge(0, 1)
    s.add_edge(1, 2)
    s.add_edge(2, 0)
    embedding = [
        EmbeddingEntry(0, Similarity.from_components(scale=1.0, angle=np.pi / 2),
                       connections=[np.array([-1.0, 0.0])]),
        EmbeddingEntry(1, Similarity.from_components(scale=0.5),
                       connections=[np.array([0.0, 1.0])]),
        EmbeddingEntry(2, Similarity.identity(),
                       connections=[np.array([0.0, -1.0]), np.array([-1.0, 0.0])]),
    ]
    return Rule(id=0, lhs="A", rhs=s, embedding=embedding, level=0, frequency=7)


def test_grammar_json_roundtrip_is_exact(tmp_path):
    g = Grammar(rules=[sample_rule()])
    p = tmp_path / "demo.ggg.json"
    g.save_json(p)
    h = Grammar.load_json(p)

    assert len(h.rules) == 1
    r0, r1 = g.rules[0], h.rules[0]
    assert r1.lhs == "A" and r1.frequency == 7
    assert r1.rhs.edges() == r0.rhs.edges()
    # similarity stored as exact matrix -> bit-for-bit round-trip
    for e0, e1 in zip(r0.embedding, r1.embedding, strict=True):
        assert np.array_equal(e0.transform.A, e1.transform.A)
        assert np.array_equal(e0.transform.b, e1.transform.b)
        for a, b in zip(e0.connections, e1.connections, strict=True):
            assert np.array_equal(a, b)


def test_grammar_with_axiom_and_frames(tmp_path):
    axiom = GeometricGraph()
    axiom.add_vertex(0, (0.0, 0.0))
    axiom.add_vertex(1, (1.0, 0.0))
    axiom.add_edge(0, 1)
    frames = {0: Similarity.from_components(angle=0.3), 1: Similarity.identity()}
    g = Grammar(rules=[sample_rule()], axiom=axiom, axiom_frames=frames)
    path = tmp_path / "a.ggg.json"
    g.save_json(path)
    h = Grammar.load_json(path)
    assert h.axiom is not None and h.axiom.num_vertices == 2
    assert np.array_equal(h.axiom_frames[0].A, frames[0].A)


def test_occurrences_roundtrip(tmp_path):
    rule = sample_rule()
    rule.occurrences = [
        Occurrence(
            transform=Similarity.from_components(scale=2.0, angle=0.5, tx=10.0, ty=-3.0),
            vertices={0: 41, 1: 42, 2: 43},
            node_position=np.array([10.5, -2.5]),
        ),
        Occurrence(transform=Similarity.identity(), vertices={0: 7, 1: 8, 2: 9}),
    ]
    g = Grammar(rules=[rule])
    path = tmp_path / "occ.ggg.json"
    g.save_json(path)
    h = Grammar.load_json(path)

    occ = h.rules[0].occurrences
    assert len(occ) == 2
    assert occ[0].vertices == {0: 41, 1: 42, 2: 43}
    assert np.allclose(occ[0].node_position, [10.5, -2.5])
    assert np.array_equal(occ[0].transform.A, rule.occurrences[0].transform.A)
    assert occ[1].node_position is None  # omitted when unset
    assert "occurrences: 2" in h.to_text()


def test_to_text_mentions_rule():
    txt = Grammar(rules=[sample_rule()]).to_text()
    assert "rule 0" in txt and "A -> S" in txt
