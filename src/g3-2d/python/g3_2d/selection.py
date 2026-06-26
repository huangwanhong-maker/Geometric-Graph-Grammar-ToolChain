"""Isogroup selection (paper Section 5.2).

Pick which isogroup to encode, and the largest set of its occurrences that do not overlap. Overlap =
sharing any input-graph vertex; the largest non-overlapping subset is the maximum clique of the dual
graph whose edges join disjoint occurrences (paper: "create a dual topological graph ... find the
largest clique"). Max clique is NP-hard, but occurrence counts are modest; we use exact
Bron-Kerbosch with deterministic ordering and fall back to a greedy cover above a size cap.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .isogroup import Isogroup, Occurrence


# Default ranking: prefer larger structures, then more frequent (paper: "the largest from the
# most-frequently-repeated isogroups is selected"). For true compression-gain ranking that accounts
# for overlap, use ``best_rule`` instead.
def _default_score(iso: Isogroup) -> tuple:
    return (iso.order, iso.frequency)


def select_isogroup(
    isogroups: Sequence[Isogroup],
    *,
    score: Callable[[Isogroup], tuple] = _default_score,
    min_order: int = 2,
) -> Isogroup | None:
    """Return the highest-scoring isogroup (default: largest, then most frequent), or ``None``."""
    candidates = [g for g in isogroups if g.order >= min_order and g.frequency >= 2]
    if not candidates:
        return None
    # max score; deterministic tie-break by canonical key
    return max(candidates, key=lambda g: (score(g), g.key))


def best_rule(
    isogroups: Sequence[Isogroup], *, min_cover: int = 2, prefer: str = "gain"
) -> tuple[Isogroup, list[Occurrence]] | None:
    """Pick the isogroup + non-overlapping cover to encode next.

    ``cover`` is the largest non-overlapping set of occurrences; vertices saved =
    ``(order - 1) * len(cover)``. Ranking depends on ``prefer``:

    * ``"gain"`` (default) - maximize vertices saved. Pure compression; on a grid this tends to pick
      L-shaped paths, and on a fractal it picks paths over triangles, because paths pack more
      disjoint copies.
    * ``"dense"`` - prefer closed/compact patterns first (higher edges-per-vertex), then gain. This
      makes the learner encode *cycles* - unit squares on a grid, triangles on a Sierpinski gasket -
      which is usually what you want for shape-structured inputs.

    Returns ``None`` if nothing clears ``min_cover`` simultaneously-replaceable occurrences.
    """
    best: tuple[Isogroup, list[Occurrence]] | None = None
    best_key: tuple | None = None
    for iso in isogroups:
        if iso.order < 2 or iso.frequency < min_cover:
            continue
        cover = non_overlapping_subset(iso.occurrences)
        if len(cover) < min_cover:
            continue
        saved = (iso.order - 1) * len(cover)
        if prefer == "dense":
            density = round(iso.pattern.num_edges / iso.order, 6)
            key = (density, saved, iso.order, iso.key)
        elif prefer == "gain":
            key = (saved, iso.order, iso.key)
        else:
            raise ValueError(f"unknown prefer mode: {prefer!r}")
        if best_key is None or key > best_key:
            best, best_key = (iso, cover), key
    return best


_CLIQUE_NODE_CAP = 60  # above this, use the greedy fallback instead of exact Bron-Kerbosch


def non_overlapping_subset(occurrences: Sequence[Occurrence]) -> list[Occurrence]:
    """Largest subset of mutually vertex-disjoint occurrences.

    Two occurrences *conflict* if they share a vertex. The answer is a maximum independent set of
    the conflict graph (equivalently the maximum clique of its complement, the disjointness graph).
    Exact via Bron-Kerbosch for small inputs; greedy independent set above ``_CLIQUE_NODE_CAP``.
    """
    occ = list(occurrences)
    n = len(occ)
    if n <= 1:
        return occ
    conflict: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if not occ[i].isdisjoint(occ[j]):
                conflict[i].add(j)
                conflict[j].add(i)

    if n > _CLIQUE_NODE_CAP:
        chosen = _greedy_independent(conflict)
    else:
        everything = set(range(n))
        disjoint = [everything - conflict[i] - {i} for i in range(n)]
        chosen = _max_clique(disjoint)
    return [occ[i] for i in sorted(chosen)]


def _greedy_independent(conflict: list[set[int]]) -> set[int]:
    """Greedy maximum independent set: repeatedly take the least-conflicting remaining vertex."""
    remaining = set(range(len(conflict)))
    chosen: set[int] = set()
    while remaining:
        # fewest conflicts within remaining, tie-break lowest index (deterministic)
        i = min(remaining, key=lambda k: (len(conflict[k] & remaining), k))
        chosen.add(i)
        remaining.discard(i)
        remaining -= conflict[i]  # exclude everything that conflicts with i
    return chosen


def _max_clique(adj: list[set[int]]) -> set[int]:
    """Exact maximum clique via Bron-Kerbosch with pivoting; deterministic best (size, then ids)."""
    best: list[set[int]] = [set()]

    def better(cand: set[int]) -> bool:
        if len(cand) != len(best[0]):
            return len(cand) > len(best[0])
        return sorted(cand) < sorted(best[0])

    def expand(r: set[int], p: set[int], x: set[int]) -> None:
        if not p and not x:
            if better(r):
                best[0] = set(r)
            return
        pivot = max(p | x, key=lambda u: len(adj[u] & p))
        for v in sorted(p - adj[pivot]):
            expand(r | {v}, p & adj[v], x & adj[v])
            p = p - {v}
            x = x | {v}

    expand(set(), set(range(len(adj))), set())
    return best[0]
