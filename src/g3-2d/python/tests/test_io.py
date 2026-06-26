import json
from pathlib import Path

from g3_2d.generators import grid_graph
from g3_2d.io import from_dict, load_json, save_json, to_dict


def test_dict_roundtrip():
    g = grid_graph(3, 4)
    h = from_dict(to_dict(g))
    assert h.vertices() == g.vertices()
    assert h.edges() == g.edges()


def test_json_file_roundtrip(tmp_path: Path):
    g = grid_graph(2, 2)
    p = tmp_path / "g.json"
    save_json(g, p)
    h = load_json(p)
    assert h.edges() == g.edges()


def test_loads_repo_fixture():
    # fixtures/ lives at the repository root: src/g3-2d/python/tests -> up 4
    root = Path(__file__).resolve().parents[4]
    fixture = root / "fixtures" / "graphs" / "two_triangles.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    g = from_dict(data)
    assert g.num_vertices == len(data["vertices"])
    assert g.num_edges == len(data["edges"])
