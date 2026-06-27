"""Offline tests for the OSM importer (no network: synthetic Overpass JSON)."""

from g3_2d.osm import osm_to_graph, road_query, simplify_degree2

SAMPLE = {
    "elements": [
        {"type": "node", "id": 1, "lat": 0.0, "lon": 0.000},
        {"type": "node", "id": 2, "lat": 0.0, "lon": 0.001},
        {"type": "node", "id": 3, "lat": 0.0, "lon": 0.002},
        {"type": "node", "id": 4, "lat": 0.001, "lon": 0.002},
        {"type": "way", "id": 100, "nodes": [1, 2, 3], "tags": {"highway": "residential"}},
        {"type": "way", "id": 101, "nodes": [3, 4], "tags": {"highway": "residential"}},
    ]
}


def test_osm_to_graph_no_simplify():
    g = osm_to_graph(SAMPLE, simplify=False)
    assert g.num_vertices == 4
    assert g.num_edges == 3  # (1,2),(2,3),(3,4)


def test_osm_to_graph_simplifies_degree2_chain():
    g = osm_to_graph(SAMPLE, simplify=True)
    # the 1-2-3-4 chain dissolves its degree-2 interior into a single edge between endpoints
    assert g.num_vertices == 2
    assert g.num_edges == 1


def test_simplify_keeps_junctions():
    # a Y-junction at the centre must survive simplification (degree 3)
    g = osm_to_graph({
        "elements": [
            {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0},
            {"type": "node", "id": 2, "lat": 0.001, "lon": 0.0},
            {"type": "node", "id": 3, "lat": -0.001, "lon": 0.001},
            {"type": "node", "id": 4, "lat": -0.001, "lon": -0.001},
            {"type": "way", "id": 1, "nodes": [2, 1], "tags": {"highway": "path"}},
            {"type": "way", "id": 2, "nodes": [1, 3], "tags": {"highway": "path"}},
            {"type": "way", "id": 3, "nodes": [1, 4], "tags": {"highway": "path"}},
        ]
    })
    assert g.has_vertex(1) and g.degree(1) == 3


def test_road_query_contains_bbox_and_filter():
    q = road_query(1.0, 2.0, 3.0, 4.0, highways="residential")
    assert "1.0,2.0,3.0,4.0" in q
    assert "residential" in q


def test_simplify_degree2_is_idempotent_on_simple_graph():
    g = osm_to_graph(SAMPLE, simplify=True)
    assert simplify_degree2(g).num_edges == g.num_edges
