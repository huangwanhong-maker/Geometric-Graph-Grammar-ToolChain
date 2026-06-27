"""Import real-world road networks from OpenStreetMap as geometric graphs (paper Section 7).

Uses the public Overpass API over stdlib ``urllib`` only (no geopandas/osmnx), so it stays
dependency-free and easy to mirror in C++. Latitude/longitude are projected to local metres with an
equirectangular projection centred on the data, which preserves shape at city scale. By default the
graph is topologically simplified - degree-2 shape points along a road are dissolved so that
vertices are road *junctions* and edges are straight segments between them (the "block" graph the
learner looks for repeated structure in).
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from typing import Any

from .graph import GeometricGraph

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_HIGHWAYS = (
    "motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street"
)
# Organic settlements also have footpaths; include them for indigenous/medina layouts.
ORGANIC_HIGHWAYS = DEFAULT_HIGHWAYS + "|pedestrian|footway|path|track"

# Presets as (south, west, north, east).
#  - regular grids (paper-style) for the European/American examples;
#  - organic / self-similar African settlements (cf. Ron Eglash, "African Fractals").
PRESETS: dict[str, tuple[float, float, float, float]] = {
    "barcelona-eixample": (41.388, 2.160, 41.395, 2.170),
    "manhattan-midtown": (40.745, -73.990, 40.760, -73.970),
    # African settlements with organic, often self-similar structure
    "fez-medina": (34.058, -4.985, 34.070, -4.968),
    "marrakesh-medina": (31.620, -8.000, 31.636, -7.980),
    "kano-old-city": (11.985, 8.505, 12.005, 8.525),
    "accra-jamestown": (5.524, -0.220, 5.534, -0.206),
    "kumasi-centre": (6.683, -1.630, 6.697, -1.616),
}


def road_query(south: float, west: float, north: float, east: float,
               highways: str = DEFAULT_HIGHWAYS) -> str:
    return (
        f"[out:json][timeout:120];"
        f'way["highway"~"{highways}"]({south},{west},{north},{east});'
        f"(._;>;);out body;"
    )


def fetch_overpass(query: str, *, url: str = OVERPASS_URL, timeout: int = 180) -> dict[str, Any]:
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "g3-2d-osm/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted endpoint)
        return json.loads(resp.read().decode("utf-8"))


def simplify_degree2(g: GeometricGraph) -> GeometricGraph:
    """Dissolve degree-2 vertices (road shape points) into edges between their neighbours."""
    h = g.copy()
    changed = True
    while changed:
        changed = False
        for v in list(h.vertices()):
            if not h.has_vertex(v):
                continue
            nb = sorted(h.neighbors(v))
            if len(nb) == 2 and nb[0] != nb[1]:
                a, b = nb
                h.remove_vertex(v)
                if not h.has_edge(a, b):
                    h.add_edge(a, b)
                changed = True
    return h


def largest_component(g: GeometricGraph) -> GeometricGraph:
    """Return the induced subgraph of the largest connected component."""
    seen: set[int] = set()
    best: list[int] = []
    for start in g.vertices():
        if start in seen:
            continue
        comp: list[int] = []
        stack = [start]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(g.neighbors(x))
        if len(comp) > len(best):
            best = comp
    return g.induced_subgraph(best) if best else g


def trim_long_edges(g: GeometricGraph, factor: float) -> GeometricGraph:
    """Drop edges longer than ``factor`` times the median edge length (clip boundary spokes)."""
    lengths = []
    for a, b in g.edges():
        pa, pb = g.position(a), g.position(b)
        lengths.append(math.hypot(pa[0] - pb[0], pa[1] - pb[1]))
    if not lengths:
        return g
    threshold = factor * sorted(lengths)[len(lengths) // 2]
    h = GeometricGraph()
    for v in g.vertices():
        h.add_vertex(v, g.position(v))
    for a, b in g.edges():
        pa, pb = g.position(a), g.position(b)
        if math.hypot(pa[0] - pb[0], pa[1] - pb[1]) <= threshold:
            h.add_edge(a, b)
    return h


def osm_to_graph(data: dict[str, Any], *, simplify: bool = True) -> GeometricGraph:
    """Convert Overpass JSON (nodes + highway ways) into a projected geometric graph."""
    coords = {
        e["id"]: (e["lat"], e["lon"]) for e in data["elements"] if e["type"] == "node"
    }
    ways = [e for e in data["elements"] if e["type"] == "way" and "nodes" in e]
    if not coords or not ways:
        raise ValueError("no road data returned (empty bbox or filtered out)")

    lat0 = sum(la for la, _ in coords.values()) / len(coords)
    lon0 = sum(lo for _, lo in coords.values()) / len(coords)
    r = 6_371_000.0
    cos_lat0 = math.cos(math.radians(lat0))

    def project(lat: float, lon: float) -> tuple[float, float]:
        x = math.radians(lon - lon0) * cos_lat0 * r
        y = math.radians(lat - lat0) * r
        return (x, y)

    edges: list[tuple[int, int]] = []
    used: set[int] = set()
    for w in ways:
        refs = [n for n in w["nodes"] if n in coords]
        for a, b in zip(refs, refs[1:], strict=False):
            if a != b:
                edges.append((a, b))
                used.add(a)
                used.add(b)

    g = GeometricGraph()
    for nid in used:
        la, lo = coords[nid]
        g.add_vertex(nid, project(la, lo))
    for a, b in edges:
        if not g.has_edge(a, b):
            g.add_edge(a, b)

    return simplify_degree2(g) if simplify else g


def download_road_network(
    south: float, west: float, north: float, east: float, *,
    highways: str = DEFAULT_HIGHWAYS, simplify: bool = True,
) -> GeometricGraph:
    data = fetch_overpass(road_query(south, west, north, east, highways))
    return osm_to_graph(data, simplify=simplify)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    from .io import save_json

    parser = argparse.ArgumentParser(
        description="Download an OSM road network as a geometric graph."
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--preset", choices=sorted(PRESETS), help="a built-in bounding box")
    src.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"),
                     help="bounding box: south west north east (lat lon lat lon)")
    parser.add_argument("--highways", default=None, help="Overpass highway regex (override)")
    parser.add_argument("--organic", action="store_true",
                        help="include footpaths/pedestrian ways (medinas, villages)")
    parser.add_argument("--no-simplify", action="store_true", help="keep road shape points")
    parser.add_argument("--largest-component", action="store_true",
                        help="keep only the largest connected component")
    parser.add_argument("--max-edge-factor", type=float, default=None,
                        help="drop edges longer than N x median (clip boundary spokes), e.g. 4")
    parser.add_argument("-o", "--out", required=True, help="output graph JSON")
    args = parser.parse_args(argv)

    highways = args.highways or (ORGANIC_HIGHWAYS if args.organic else DEFAULT_HIGHWAYS)
    s, w, n, e = PRESETS[args.preset] if args.preset else args.bbox
    print(f"querying Overpass for highways in ({s}, {w}, {n}, {e}) ...")
    g = download_road_network(s, w, n, e, highways=highways, simplify=not args.no_simplify)
    if args.max_edge_factor:
        g = trim_long_edges(g, args.max_edge_factor)
    if args.largest_component:
        g = largest_component(g)
    save_json(g, args.out)
    print(f"wrote {args.out}: {g.num_vertices} vertices, {g.num_edges} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
