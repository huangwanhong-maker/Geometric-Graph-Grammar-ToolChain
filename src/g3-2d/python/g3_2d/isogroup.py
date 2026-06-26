"""Isogroups: groups of geometrically-isomorphic repeated subgraphs (paper Section 5).

An *isogroup* is one repeated pattern plus every place it occurs in the input graph. Because we work
with **induced** subgraphs, an occurrence is fully determined by its vertex set, so we store
occurrences as frozensets of input-graph vertex ids. All occurrences of an isogroup share one
canonical key (they are geometrically isomorphic).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .graph import GeometricGraph
from .isomorphism import CanonicalKey

Occurrence = frozenset[int]  # a set of input-graph vertex ids (induced subgraph)


@dataclass
class Isogroup:
    """A repeated pattern (canonical key + representative subgraph) and all its occurrences."""

    key: CanonicalKey
    pattern: GeometricGraph                       # representative induced subgraph (world coords)
    occurrences: list[Occurrence] = field(default_factory=list)

    @property
    def order(self) -> int:
        """Number of vertices in the pattern (the graph 'order')."""
        return self.pattern.num_vertices

    @property
    def frequency(self) -> int:
        """How many times the pattern repeats in the input."""
        return len(self.occurrences)

    @property
    def gain(self) -> int:
        """Rough compression gain: vertices removed if every occurrence is replaced by one node."""
        return self.frequency * (self.order - 1)

    def add_occurrence(self, occ: Occurrence) -> None:
        self.occurrences.append(occ)

    def __repr__(self) -> str:
        return f"Isogroup(order={self.order}, freq={self.frequency})"
