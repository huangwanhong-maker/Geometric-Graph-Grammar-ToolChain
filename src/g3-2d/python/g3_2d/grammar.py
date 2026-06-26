"""Geometric graph grammar representation and serialization (paper Section 3.2).

This module defines the **output artifact** of learning: a grammar is a set of production rules

    q -> S / B                                                              (Eqn. 1)

where ``q`` is the replaced (non-terminal) symbol, ``S`` is the replacement subgraph, and ``B`` is
the geometric embedding

    B = { (v_i, T_i, {p_i0, p_i1, ...}) }                                   (Eqn. 2)

with ``v_i`` a vertex of ``S``, ``T_i`` the local coordinate frame of ``v_i`` (a similarity), and
``p_ij`` the relative positions of expected neighbours that ``v_i`` connects back to.

A learned grammar serializes to a single ``*.ggg.json`` file (schema documented in
``fixtures/README.md``); ``to_text`` gives a human-readable dump. Similarity transforms are stored
as their exact ``2x2`` linear part + translation so the file round-trips bit-for-bit across the
four implementations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .geometry import Similarity
from .graph import GeometricGraph

FORMAT = "ggg-2d"
FORMAT_VERSION = 1


# --------------------------------------------------------------------------------------------------
# Similarity <-> JSON (exact matrix form; no scale/angle decomposition, so it round-trips exactly)
# --------------------------------------------------------------------------------------------------
def transform_to_dict(t: Similarity) -> dict[str, Any]:
    return {"linear": t.A.tolist(), "translation": t.b.tolist()}


def transform_from_dict(d: dict[str, Any]) -> Similarity:
    return Similarity(
        np.asarray(d["linear"], dtype=float), np.asarray(d["translation"], dtype=float)
    )


# --------------------------------------------------------------------------------------------------
# Embedding entry:  (v_i, T_i, {p_ij})
# --------------------------------------------------------------------------------------------------
@dataclass
class EmbeddingEntry:
    """How one RHS vertex re-attaches to the surrounding graph."""

    vertex: int                                   # local vertex id in the rule's RHS subgraph
    transform: Similarity                         # local coordinate frame T_i
    connections: list[np.ndarray] = field(default_factory=list)  # relative positions p_ij

    def to_dict(self) -> dict[str, Any]:
        return {
            "vertex": self.vertex,
            "transform": transform_to_dict(self.transform),
            "connections": [list(map(float, p)) for p in self.connections],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> EmbeddingEntry:
        return EmbeddingEntry(
            vertex=int(d["vertex"]),
            transform=transform_from_dict(d["transform"]),
            connections=[np.asarray(p, dtype=float) for p in d.get("connections", [])],
        )


# --------------------------------------------------------------------------------------------------
# Occurrence:  where a rule fired in the input graph (world placement, for re-rendering / debugging)
# --------------------------------------------------------------------------------------------------
@dataclass
class Occurrence:
    """One concrete instance of a rule's subgraph in the input graph.

    ``transform`` maps the rule's RHS-local coordinates to the world (input-graph) coordinates of
    this instance; ``vertices`` maps each RHS-local vertex id to the input-graph vertex id it
    matched; ``node_position`` is the world position chosen for the replacement node ``q`` (if any).
    """

    transform: Similarity
    vertices: dict[int, int] = field(default_factory=dict)  # rhs-local id -> input-graph id
    node_position: np.ndarray | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "transform": transform_to_dict(self.transform),
            "vertices": [[int(k), int(v)] for k, v in sorted(self.vertices.items())],
        }
        if self.node_position is not None:
            d["node"] = list(map(float, self.node_position))
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Occurrence:
        node = d.get("node")
        return Occurrence(
            transform=transform_from_dict(d["transform"]),
            vertices={int(k): int(v) for k, v in d.get("vertices", [])},
            node_position=None if node is None else np.asarray(node, dtype=float),
        )


# --------------------------------------------------------------------------------------------------
# Production rule:  q -> S / B
# --------------------------------------------------------------------------------------------------
@dataclass
class Rule:
    """A single production rule ``q -> S / B``."""

    id: int
    lhs: str                                       # the non-terminal symbol q being replaced
    rhs: GeometricGraph                            # the replacement subgraph S (local coordinates)
    embedding: list[EmbeddingEntry] = field(default_factory=list)
    level: int = 0                                 # hierarchy level (0 = first learned)
    frequency: int = 0                             # occurrences in the input (learned rules)
    rhs_symbols: dict[int, str] = field(default_factory=dict)  # non-terminal RHS verts (optional)
    occurrences: list[Occurrence] = field(default_factory=list)  # world placements (optional)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "frequency": self.frequency,
            "lhs": {"symbol": self.lhs},
            "rhs": {
                "vertices": [
                    {
                        "id": v,
                        "x": float(self.rhs.position(v)[0]),
                        "y": float(self.rhs.position(v)[1]),
                        **({"symbol": self.rhs_symbols[v]} if v in self.rhs_symbols else {}),
                    }
                    for v in self.rhs.vertices()
                ],
                "edges": [list(e) for e in self.rhs.edges()],
            },
            "embedding": [e.to_dict() for e in self.embedding],
            **(
                {"occurrences": [o.to_dict() for o in self.occurrences]}
                if self.occurrences else {}
            ),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Rule:
        rhs = GeometricGraph()
        rhs_symbols: dict[int, str] = {}
        for rec in d["rhs"]["vertices"]:
            vid = int(rec["id"])
            rhs.add_vertex(vid, (float(rec["x"]), float(rec["y"])))
            if "symbol" in rec:
                rhs_symbols[vid] = str(rec["symbol"])
        for u, v in d["rhs"].get("edges", []):
            rhs.add_edge(int(u), int(v))
        return Rule(
            id=int(d["id"]),
            lhs=str(d["lhs"]["symbol"]),
            rhs=rhs,
            embedding=[EmbeddingEntry.from_dict(e) for e in d.get("embedding", [])],
            level=int(d.get("level", 0)),
            frequency=int(d.get("frequency", 0)),
            rhs_symbols=rhs_symbols,
            occurrences=[Occurrence.from_dict(o) for o in d.get("occurrences", [])],
        )


# --------------------------------------------------------------------------------------------------
# Grammar = axiom + rules
# --------------------------------------------------------------------------------------------------
@dataclass
class Grammar:
    """A geometric graph grammar: a start configuration (axiom) plus production rules."""

    rules: list[Rule] = field(default_factory=list)
    axiom: GeometricGraph | None = None
    axiom_frames: dict[int, Similarity] = field(default_factory=dict)
    dimension: int = 2
    transform_class: str = "similarity"

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    # -- serialization -------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        axiom: dict[str, Any] | None = None
        if self.axiom is not None:
            axiom = {
                "vertices": [
                    {
                        "id": v,
                        "x": float(self.axiom.position(v)[0]),
                        "y": float(self.axiom.position(v)[1]),
                        **(
                            {"frame": transform_to_dict(self.axiom_frames[v])}
                            if v in self.axiom_frames else {}
                        ),
                    }
                    for v in self.axiom.vertices()
                ],
                "edges": [list(e) for e in self.axiom.edges()],
            }
        return {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "dimension": self.dimension,
            "transform_class": self.transform_class,
            "axiom": axiom,
            "rules": [r.to_dict() for r in self.rules],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Grammar:
        axiom = None
        axiom_frames: dict[int, Similarity] = {}
        if d.get("axiom"):
            axiom = GeometricGraph()
            for rec in d["axiom"]["vertices"]:
                vid = int(rec["id"])
                axiom.add_vertex(vid, (float(rec["x"]), float(rec["y"])))
                if "frame" in rec:
                    axiom_frames[vid] = transform_from_dict(rec["frame"])
            for u, v in d["axiom"].get("edges", []):
                axiom.add_edge(int(u), int(v))
        return Grammar(
            rules=[Rule.from_dict(r) for r in d.get("rules", [])],
            axiom=axiom,
            axiom_frames=axiom_frames,
            dimension=int(d.get("dimension", 2)),
            transform_class=str(d.get("transform_class", "similarity")),
        )

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def load_json(path: str | Path) -> Grammar:
        return Grammar.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    # -- human-readable dump -------------------------------------------------------------------
    def to_text(self) -> str:
        lines = [
            f"# geometric graph grammar ({self.transform_class}, {self.dimension}D)",
            f"# {len(self.rules)} rule(s)",
        ]
        if self.axiom is not None:
            lines.append(f"axiom: {self.axiom.num_vertices} vertices, {self.axiom.num_edges} edges")
        for r in self.rules:
            lines.append("")
            lines.append(
                f"rule {r.id} (level {r.level}, freq {r.frequency}): "
                f"{r.lhs} -> S[{r.rhs.num_vertices}v,{r.rhs.num_edges}e] / B"
            )
            for v in r.rhs.vertices():
                p = r.rhs.position(v)
                sym = r.rhs_symbols.get(v)
                tag = f" :{sym}" if sym else ""
                lines.append(f"    v{v}{tag} @ ({p[0]:.3f}, {p[1]:.3f})")
            for e in r.embedding:
                conns = ", ".join(f"[{p[0]:.3f}, {p[1]:.3f}]" for p in e.connections)
                lines.append(
                    f"    embed v{e.vertex}: scale {e.transform.scale:.3f}, "
                    f"angle {np.degrees(e.transform.rotation):.1f} deg -> {{{conns}}}"
                )
            if r.occurrences:
                lines.append(f"    occurrences: {len(r.occurrences)} (world placements recorded)")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Grammar({len(self.rules)} rules, {self.dimension}D, {self.transform_class})"
