# G³ 2D — Python

The reference Python implementation of 2D geometric graph grammars (learning + generation).
This is the first of the four implementations to be built; its module breakdown and the shared
`fixtures/` it consumes serve as the specification the other three implementations validate against.

See [../../../docs/ALGORITHM_NOTES.md](../../../docs/ALGORITHM_NOTES.md) for the algorithm.

## Design principles

- **Self-implemented core, NumPy only.** The substance of the paper — geometric isomorphism, polar-
  grid vertex expansion, dual-graph clique selection — is our own code, not delegated to a graph
  library, so the C++ port can mirror it 1:1. (qhull is reserved for 3D convex hulls.)
- **Similarity transforms.** Geometric isomorphism is taken up to rotation + uniform scale +
  translation (orientation-preserving). No reflection, no shear.
- **Determinism.** Every tie (canonical frame, sort order, …) is broken by a total, documented rule
  so output is reproducible and matches the other implementations bit-for-bit.

## Status — foundation landed

| Module | Purpose | State |
|---|---|---|
| `g3_2d/geometry.py` | similarity transforms, convex-hull area, polar grid | ✅ done |
| `g3_2d/graph.py` | `GeometricGraph`, induced subgraph | ✅ done |
| `g3_2d/isomorphism.py` | canonical key + geometric isomorphism | ✅ done |
| `g3_2d/io.py` | JSON load/save (shared fixture format) | ✅ done |
| `g3_2d/generators.py` | synthetic graphs (grid, jitter) | ✅ done |
| `g3_2d/grammar.py` | grammar/rule representation + `*.ggg.json` serialization | ✅ done |
| `g3_2d/viz.py` | matplotlib visualization (optional `viz` extra) | ✅ done |
| `g3_2d/expansion.py` | vertex expansion (two polar grids) | ✅ done |
| `g3_2d/detection.py` | isogroup detection loop | ✅ done |
| `g3_2d/selection.py` | isogroup selection (max-clique non-overlap) | ✅ done |
| `g3_2d/encoder.py` | grammar encoder (RHS `S`, embedding `B`, occurrences) | ✅ done |
| `g3_2d/learn.py` | inverse-modeling driver (detect→select→encode→rewrite) | ✅ done |
| `g3_2d/forward.py` | forward generator (grammar → graph, fractals) | ✅ done |
| `g3_2d/examples.py` | example grammars (Sierpinski triangle, paper Fig. 12) | ✅ done |
| `g3_2d/parse.py` | syntax analysis: parse a geometry against a grammar + reconstruct | ✅ done |
| `g3_2d/osm.py` | import OpenStreetMap road/path networks (real-world maps) | ✅ done |
| `g3_2d/eeg.py` | EEG phase-space reconstruction → 2D trajectory graph | ✅ done |

The **output artifact** of learning is a `*.ggg.json` grammar file (one production rule `q → S / B`
per learned isogroup, with the world `occurrences` of each rule recorded). See
`fixtures/expected/demo_triangle.ggg.json` for the format, and `Grammar.to_text()` for a dump.

## Learn a grammar (induction → analysis → visualization)

```sh
# learn, print an analysis report, write the grammar, save a JSON report, draw the occurrences
python -m g3_2d <graph.json> -o out.ggg.json --report report.json --draw fired.png --max-order 4
```
Flags: `--text` (readable rule dump), `--report PNG.json` (analysis as JSON), `--draw PNG`
(input graph with each level-0 rule's occurrences colour-coded), `--quiet` (suppress the report).
The report prints the order-by-order isogroup counts, a per-rule table (order/freq/encoded/saved),
and the overall compression. You can also drive the visualizer directly:

```sh
python -m g3_2d.viz <graph.json> --groups 0,1,2 3,4,5 -o fired.png   # colour specific vertex sets
```

`learn(graph, *, max_levels=16, max_order=6, min_frequency=2, frequency_cut=0.0,
placement="existing")` returns a `Grammar`. `max_order` bounds the largest pattern per level
(keep it small on big inputs); `frequency_cut` enables the paper's ~0.8 least-frequent pruning for
speed (default 0.0 = full/ground-truth analysis).

## Forward generation (fractals, paper Fig. 12)

The generative direction: apply a recursive grammar to grow a structure (turtle-style frame
composition). Reproduce the paper's Sierpinski triangle:

```sh
python -m g3_2d.examples sierpinski -n 6 -o sierpinski.png
```

In code, `generate(grammar, iterations)` takes a `ForwardGrammar` (axiom modules + productions +
per-symbol terminal shapes) and returns a `GeometricGraph`. See `g3_2d/examples.py:sierpinski`.

## Syntax analysis (parse a geometry against a grammar)

The recognition counterpart of learning: given a geometry **and** a grammar, reduce the geometry by
the grammar's rules, recording the **derivation** (which rule fired where, in what order). Replaying
the derivation in reverse regenerates the geometry exactly.

```sh
# learn a grammar, then analyze the geometry with it: process + per-step PNGs + JSON + reconstruction
python -m g3_2d <graph.json> -o g.ggg.json --max-order 4 --prefer dense --quiet
python -m g3_2d.parse <graph.json> g.ggg.json \
    --steps-dir steps/ --record trace.json --reconstruct rebuilt.png
```

This prints the step-by-step derivation, writes one PNG per reduction step (occurrences colour-coded)
plus `reduced_axiom.png`, saves the derivation as JSON, and reconstructs the geometry (reporting
whether it matches the input). In code: `parse(graph, grammar)` → `ParseResult` (steps + reduced
graph), and `reconstruct(result)` → `GeometricGraph`.

## Setup

```sh
python -m venv .venv && . .venv/Scripts/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Test & lint

```sh
pytest          # unit tests + shared-fixture checks
ruff check .    # lint
```
