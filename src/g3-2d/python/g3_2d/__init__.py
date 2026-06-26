"""G3-2D: Geometric Graph Grammars in 2D.

Reference Python implementation of Fiser et al. (SCCG'16), "Learning Geometric Graph Grammars".
See ``docs/ALGORITHM_NOTES.md`` at the repository root for the algorithm this package implements.

This implementation is the executable specification that the other three implementations
(2D-C++, 3D-Python, 3D-C++) are validated against, so it favours explicit, deterministic logic
over library magic. Geometric isomorphism is taken up to *similarity* transforms (rotation,
uniform scale, translation) by default - no reflection, no shear.
"""

from __future__ import annotations

from .detection import detect_isogroups
from .encoder import encode_rule
from .forward import ForwardGrammar, Production, generate
from .geometry import (
    PolarGrid,
    Similarity,
    centroid,
    convex_hull,
    convex_hull_area,
)
from .grammar import EmbeddingEntry, Grammar, Occurrence, Rule
from .graph import GeometricGraph
from .isogroup import Isogroup
from .learn import learn
from .selection import best_rule, non_overlapping_subset, select_isogroup

__all__ = [
    "Similarity",
    "convex_hull",
    "convex_hull_area",
    "PolarGrid",
    "centroid",
    "GeometricGraph",
    "Grammar",
    "Rule",
    "EmbeddingEntry",
    "Occurrence",
    "Isogroup",
    "detect_isogroups",
    "select_isogroup",
    "best_rule",
    "non_overlapping_subset",
    "encode_rule",
    "learn",
    "ForwardGrammar",
    "Production",
    "generate",
]

__version__ = "0.0.1"
