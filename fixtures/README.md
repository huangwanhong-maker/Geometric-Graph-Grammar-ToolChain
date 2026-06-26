# Shared fixtures (cross-implementation oracle)

Language-neutral test cases that **all four** implementations (2D/3D × Python/C++) run against, so
they stay provably in agreement. Each implementation keeps its own unit tests too; these fixtures are
the shared ground truth.

## Layout

```
fixtures/
  graphs/     input geometric graphs (JSON)
  expected/   expected outputs: induced grammars (*.ggg.json) and analysis results
```

## Grammar file (`*.ggg.json`) — the learning output artifact

The primary output of learning is a grammar file: an axiom plus a list of production rules
`q → S / B` (paper Eqn. 1–2). Each rule stores the replaced symbol `q`, the replacement subgraph
`S` (vertices with local coordinates + edges), and the embedding `B` — per RHS vertex, its local
coordinate frame `T_i` (a similarity, stored as an exact 2×2 linear part + translation so it
round-trips bit-for-bit) and the relative positions `p_ij` of the neighbours it reconnects to.
`fixtures/expected/demo_triangle.ggg.json` is a worked example (the paper's Figure 3 rule).

Each rule may also carry an optional **`occurrences`** array recording every place it fired in the
input graph: the `transform` mapping RHS-local coordinates to world coordinates, the `vertices`
mapping (RHS-local id → input-graph id), and the world `node` position chosen for the replacement
node. These let a decoder re-render the original graph and let the visualizer colour where each rule
applied.

## Graph JSON schema

```json
{
  "vertices": [{"id": 0, "x": 0.0, "y": 0.0}, ...],
  "edges": [[0, 1], [1, 2], ...]
}
```

- `id` — integer vertex id (unique).
- `x`, `y` — 2D coordinates (floats). (3D fixtures will add `z`.)
- `edges` — unordered pairs of ids; simple graph (no loops, no parallel edges).

## Conventions for `expected/` (forthcoming)

Because the algorithm is full of ties (best polar cell, largest isogroup, clique choice), every
implementation must apply the **same deterministic tie-breaking** documented in
`docs/ALGORITHM_NOTES.md`. Expected outputs will record canonical keys of detected isogroups and the
generated rules, not raw floating-point coordinates, so they compare exactly across languages.
