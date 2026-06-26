"""Serialization for geometric graphs.

JSON schema (the language-neutral format consumed by the shared ``fixtures/`` oracle)::

    {
      "vertices": [{"id": 0, "x": 0.0, "y": 0.0}, ...],
      "edges": [[0, 1], [1, 2], ...]
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .graph import GeometricGraph


def to_dict(g: GeometricGraph) -> dict[str, Any]:
    return {
        "vertices": [
            {"id": v, "x": float(g.position(v)[0]), "y": float(g.position(v)[1])}
            for v in g.vertices()
        ],
        "edges": [list(e) for e in g.edges()],
    }


def from_dict(data: dict[str, Any]) -> GeometricGraph:
    g = GeometricGraph()
    for rec in data["vertices"]:
        g.add_vertex(int(rec["id"]), (float(rec["x"]), float(rec["y"])))
    for u, v in data.get("edges", []):
        g.add_edge(int(u), int(v))
    return g


def save_json(g: GeometricGraph, path: str | Path) -> None:
    Path(path).write_text(json.dumps(to_dict(g), indent=2), encoding="utf-8")


def load_json(path: str | Path) -> GeometricGraph:
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
