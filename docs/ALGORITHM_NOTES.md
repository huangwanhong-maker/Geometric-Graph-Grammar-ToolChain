# Learning Geometric Graph Grammars — Algorithm Notes

> Source: Fiser, Benes, Garcia Galicia, Abdul-Massih, Aliaga, Krs (Purdue University).
> *Learning Geometric Graph Grammars*, SCCG'16. ACM DOI: 10.1145/2948628.2948635.
> These notes are my (Claude's) careful reading of the paper + its figures, written to be the
> conceptual reference for implementing the toolchain. File/figure references below point to the
> paper PDF in `docs/paper/`.

---

## 0. One-paragraph summary

The paper introduces **Geometric Graph Grammars (GGG)** — an extension of Node-Label-Controlled
(NLC) graph grammars that encode **both topology and geometry** (vertex 2D coordinates) — and an
algorithm for **learning** such a grammar from an input geometric graph (inverse procedural
modeling). Learning = data compression: find frequently repeated subgraphs ("isogroups"), replace
each occurrence with a single node, and emit a rewriting rule that can regenerate it. The process is
hierarchical (replace, then re-analyze the smaller graph, repeating to build levels). Demonstrated on
urban road networks (OpenStreetMap). Learning a 72k-vertex / 100k-edge network takes < 1 minute.

Two claimed contributions:
1. **Definition** of a geometric graph grammar encoding topology + geometry.
2. **Algorithm** for learning geometric graph grammars (inverse procedural modeling).

---

## 1. Core definitions (Section 3.1–3.2)

### Geometric graph
- Graph `G = (V, E)`; `E = { e = {a,b} | a,b ∈ V, a ≠ b }`.
- **Simple**: unweighted, undirected, no loops, no parallel edges.
- **Geometric graph**: every vertex `v` has a 2D position `c(v) = (x, y)`.

### Geometric isomorphism (KEY concept)
Two graphs `G`, `H` are **geometrically isomorphic** when there exists:
- a bijection `f : V_G → V_H` with `{a,b} ∈ E_G  ⇔  {f(a), f(b)} ∈ E_H` (topological iso), AND
- a transformation `T : R² → R²` such that `T(c(a)) = c(f(a))` for all `a ∈ V_G`
  (i.e. after applying `T`, corresponding vertices coincide geometrically).
- `T` is restricted to **affine** transformations (translation, rotation, scale; the paper's
  examples use rotation+scale+translation — "invariant to rotation, translation or scaling").

### Isogroup
- Given a set of graphs `X = {G1,…,Gn}`, `X` is an **isogroup** if all `Gi` are geometrically
  isomorphic to each other. (An isogroup = one repeated "pattern" + all its occurrences.)

### Induced subgraph
- `S = (V_S, E_S)` is a subgraph of `G` if `V_S ⊆ V`, `E_S ⊆ E`.
- `S` is **induced** iff `E_S` = ALL edges of `E_G` with both endpoints in `V_S`.
- Learning works with **induced** subgraphs (important: this is why the same isogroup can be
  reached from multiple expansion directions → needs isomorphism-based dedup).
- Figure 2: graph `G` with vertices {a,b,c,d,e}; induced subgraph `S` on {a,b,c,e} must include every
  G-edge among those vertices and no others.

---

## 2. The grammar (Section 3.2–3.3)

A **context-free, deterministic, non-parametric** GGG replaces a *single node* with a *graph*.

### Production rule form
```
q → S / B            (Eqn. 1)
```
- `q` = the replaced node (left-hand side, a single node).
- `S` = the subgraph that replaces `q` in the main graph `G`.
- `B` = the **geometric graph embedding** (defines how `S` connects back into the surrounding graph).

### Embedding (Eqn. 2)
```
B = { (v0, T0, {p00, p01, …}),
      (v1, T1, {p10, p11, …}),
      …
      (vn, Tn, {pn0, pn1, …}) }
```
- `vi ∈ S` : a vertex of the replacement subgraph.
- `Ti` : transformation of the **local coordinate system** of `vi` (defines orientation/scale for
  the next rule placement — analogous to the L-system turtle frame).
- `pij = [xij, yij]` : coordinates (relative to `vi`) of **expected/anticipated** vertices in the
  surrounding graph `G` that `vi` should connect to. (Gray nodes in Figure 3.)

### Worked example (Figure 3)
```
S = ({a,b,c}, {(a,b),(b,c),(c,a)})           # a triangle
B = { (a, Rotate 90°, {[-1, 0]}),
      (b, Scale 1/2,  {[0, 1]}),
      (c, I,          {[0,-1], [-1,0]}) }     # I = identity; c has TWO embedding edges
```
- Gray circles/edges in Fig 3 = expected vertices in `G` where the subgraph attaches.
- Red arrows = one axis of the transformed local coordinate system used to place the *next* rule.

### Turtle / geometry generation
- Unlike L-systems (linear strings, geometry computed in a post-pass by the turtle), in a GGG a
  geometry change affects the graph **globally**, so topology + geometry are generated in a
  **single pass**. Each vertex stores its transformation `Ti` (its local coordinate frame).
- The **axiom ω** (start symbol) must explicitly provide the initial transformation.

### Rule application — 4 steps (Section 3.2)
For replacing node `qi ∈ G`:
1. Transform the rule into the local coordinate system of `qi` according to `Ti`.
2. Erase `qi` and its incident edges.
3. Place `S` relative to `qi` inside `G`.
4. Connect embedding `B`: connect vertices of the placed `S` instance to those vertices in `G` that
   lie at the embedding location `pi = [xi, yi]` indicated by `Bi`.

### Relaxed embedding (Section 3.3) — IMPORTANT practical relaxation
- Strict embedding (every subgraph node must embed ALL its expected vertices) is too restrictive —
  a vertex that can't embed its whole subgraph couldn't be replaced.
- **Relaxed**: rewriting is **always allowed even with partial connectivity**. An expected embedding
  vertex connects only **if** a real vertex exists within a system-imposed distance threshold.
- Figure 5: node `d` replaced by a subgraph; depending on `d`'s local frame orientation the embedding
  may connect to nothing (iii, identity → too far), or to vertex `b` (iv), or to vertices `a,c` (v),
  after ±45° rotation. The rule still executes even when nothing connects.

---

## 3. Learning pipeline overview (Section 4, Figure 4)

```
Geometric Graph
      │
      ▼
┌──────────────────────── GRAPH ANALYZER ────────────────────────┐
│  ┌─ Isogroup Detection ─┐        ┌─ Isogroup Selection ─┐        │
│  │  Vertex Expansion    │        │  Find the Best        │       │
│  │  Discard Non-Frequent│        │     Isogroup          │       │
│  │     Isogroups        │        │  Find Non-Overlapping │       │
│  │  Expand More? ───loop│        │     Subgraphs         │       │
│  └──────────────────────┘        │  More Isogroups?─loop │       │
│                                   └───────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
      │  (output: "Most Frequently Repeating Patterns: isogroups")
      ▼
┌──────────────── GRAPH GRAMMAR ENCODER ─────────────────┐
│   Subgraph Encoding  →  New Node Location               │
└─────────────────────────────────────────────────────────┘
      │
      ▼
Geometric Graph Grammar       (then loop whole thing for next hierarchy level)
```

- **Graph Analyzer**: finds isogroups (groups of geometrically-isomorphic repeated subgraphs).
  Built **bottom-up**: start from a single edge → one isogroup. Iteratively expand each isogroup by
  one node until a max graph size. Selection picks the largest isogroup satisfying constraints
  (e.g. overlap-free). Repeat until no further isogroups.
- **Graph Grammar Encoder**: turns each selected isogroup into rewriting rules — replaces each
  occurrence of the isogroup's subgraph by a single new vertex, erases the subgraph, embeds the new
  vertex by connecting to its neighbors, emits a rule.
- **Hierarchical**: after replacement the (smaller) graph is encoded again → higher hierarchy level.
- **User-assisted variant**: search can be seeded by a user-selected subgraph instead of a single
  edge (faster; injects human intuition). See Figure 17.

---

## 4. Graph Analyzer (Section 5)

Motivation: like data compression — find a grammar that efficiently codifies large and/or
frequently-repeated structures.

### 4.1 Isogroup Detection (Section 5.1) — bottom-up vertex expansion

Goal: find all isogroups of the most frequently repeating subgraphs by **iteratively expanding**
previously found isogroups.

- **Seed graph `F`**: simplest case = a single edge (user-assisted: a user-selected subgraph).
- Iteratively expand `F` by **adding one vertex**, keeping only expansions that are frequently
  repeated in the input. As graphs grow, occurrence count drops.

#### Order-by-order expansion (Figure 7)
- Start: a single edge = single isogroup containing all edges (first row, "Order 2").
- Expand both endpoints → **Order 3** graphs (3 vertices); repetition count = multiplicity of the
  added vertex.
- Expand most-frequent groups → **Order 4**, then 5, 6, … until no more structures detectable.
- Each iteration yields all subgraphs of the given order + their repetition counts.
- **Merging**: the *same* graph can be reached by expanding from different directions → these are
  detected as isomorphic and merged (the "circular inset" in Fig 7 shows an Order-5 graph reached
  from different Order-4 patterns being merged).

#### Vertex expansion heuristics (how to choose the new vertex `q`)
Given a frequently-repeated graph `F`, look at vertices across ALL occurrences of `F` and pick new
vertex `q` to maximize a combination of two heuristics:
1. **Frequency** — the resulting (F + q) graph is the most frequently repeated in the input.
2. **Area** — the new vertex increases the **area of the convex hull** of the graph.
   - Rationale: prevents the algorithm from picking long edges; "generates results that prefer
     bifurcations" (branchy structures rather than long thin chains).

#### Discretized polar grids (Figure 6) — the mechanism for testing expansions
Testing many candidate expansions per vertex is expensive → simplify using **two discrete grids in
polar coordinates** (centered on the expanded vertex):
1. **Candidate-vertex counter** `f(α, d)` — count of candidate vertices falling in each polar cell
   (`α` = angle bin, `d` = radial/distance bin). Notation `Δa(α,d)`. (Fig 6b)
2. **Added-area grid** — weighted contribution to the newly added convex-hull area per cell. (Fig 6c)

Procedure:
- **Normalize** each expanded-graph occurrence to a canonical form: expanded vertex at the origin,
  all occurrences aligned to each other (same scale & rotation). (`v` at origin in Fig 6a.)
- Traverse all occurrences of the graph; for each candidate expansion vertex, increment its
  corresponding cells in BOTH grids.
- After all vertices visited, **score each cell = frequency × area** (Fig 6d).
- Pick the **highest-scoring cell**. Place new vertex `q` at the **center** of that cell; add an edge
  connecting `q` to `F`. (Fig 6e)

Why discretize: quantizes the vertex neighborhood, avoids numerical-precision issues, speeds up
evaluation.

#### Grid resolution (Figures 6, 8, 11)
- Lower resolution (bigger cells) → **fewer** detected subgraphs but **more similar** to each other.
- Higher resolution → **more** subgraphs, less mutual similarity, but **better reconstruction**
  fidelity when decoded back (Fig 11: 10×12 had artifacts; 20×24 better resembled the original).
- Default used in the paper: **10 × 12 cells** (except Fig 6 which shows smooth transitions).
- Fig 8 example: 6×8 → 15 subgraphs, 10×12 → 13, 20×24 → 9.

#### Accelerating the search (Section 5.1) — two pruning observations
Number of generated isogroups via expansion can be huge. Two accelerations:

1. **Frequency-based removal** (Figure 9): sort isogroups by repetition count; discard a percentage
   of the least-frequent ("last") isogroups each iteration. Cut value is **smaller at the start**
   (early isogroups are not yet well-formed). Empirically the threshold could be ~90% but they use a
   conservative **80%** with no significant performance hit. Done FIRST (cheap).
2. **Isomorphism-based removal**: because subgraphs are **induced**, the same isogroup can be found
   from different search directions → merge isomorphic graphs after each vertex expansion. But
   isomorphism testing is slow (must check BOTH topological AND geometric isomorphism, Sec 3.2), so
   it is performed **AFTER** frequency-based removal (only on the survivors).

Output of detection: a **frequency table** storing each isogroup, its repetition count, its
embedding, and the actual locations in the input graph. Detected subgraphs **can overlap**.

### 4.2 Isogroup Selection (Section 5.2)
- Isogroup size (graph order) is controlled either explicitly (number of iterations) or implicitly
  (stop when no expansion is possible). Most paper examples use complete analysis.
- Select the **largest among the most-frequently-repeated** isogroups.
- Optional **geometric constraints**: e.g. near-to-1 aspect ratio, or many leaves ("spiders").
  (See Fig 18 — different criteria per city.)
- Among all subgraph occurrences of the chosen isogroup, find the **largest non-overlapping subset**:
  - Build a **dual topological graph**: each occurrence = a node; connect two nodes by an edge iff
    the two occurrences are **non-overlapping**.
  - Find the **largest clique** in this dual graph → the biggest mutually-non-overlapping set.
- Proceed until no other isogroup is available. Output = list of isogroups sorted by frequency.

---

## 5. Graph Grammar Encoder (Section 6)

Input: ordered list of selected isogroups. Output: GGG rules with embeddings.

### Right-hand side (RHS) rule generation
- The isogroup already carries: subgraph `S`, its occurrences, and per-occurrence embedding `Bi`
  (Eqn. 2). `S` is unique but its embedding/transformations vary per instance.
- This info is **simply copied** into the rule.

### Left-hand side (LHS) generation — where to place the new node (Figure 10)
The LHS is a single new node replacing the subgraph. Choosing its location matters:
- (b) **Center of the subgraph** → causes **star-like artifacts**, changes graph appearance, and
  causes decoding difficulties in later iterations. (Bad.)
- (c) **At the position of an existing vertex** of the subgraph → better; connecting edges can still
  be visually distracting. For road networks they place the node near **higher-importance streets**
  (arterials/highways), which **minimizes the angles** between original graph and embedding edges.
- (d) Further improved by **not rendering some edges** (the new node's embedding stores connections
  to all original subgraph nodes — `pij` in Eqn. 2 — so edges need not all be kept when substituting).
- Placement choice is **application-dependent** (urban graph vs 2D art, etc.).

### Hierarchical encoding
- Once subgraphs are replaced by nodes, re-run learning on the new graph for higher-level rules.

---

## 6. Forward generation (Section 7, Figure 12)

GGGs can produce recursive structures (e.g. a recursive **Sierpinski triangle**):
- Axiom = a triangle with nodes labeled `P`. Each axiom vertex has a local coordinate system
  oriented along the edge to its anticlockwise neighbor (red arrow).
- Rule 1: replace vertex `P` with itself + the structure forming the rest of each triangle. Each
  transformation in the non-terminal scales by 1/2 and rotates by 0°, 120°, 240°.
- Rule 2: replace each vertex `H` with a more complex structure.
- All rules applied **in parallel**.

---

## 7. Results & evaluation highlights (Section 7)

- Implementation: **C++**, **BGL (Boost Graph Library)** for graph representation, **Qt** for direct
  rendering, **OpenStreetMap** files as input. Multi-core (8 cores, i7 @ 3.2 GHz, 16 GB).
- **Inverse modeling (Fig 13)**: full encoding of Paris into a single node — 12 min automatic
  analysis, 37 hierarchy levels, **3,098 rules**.
- **Noise sensitivity (Fig 14)**: regular grid, detect size-4 rectangles. Found 100% with no noise;
  still found all subgraphs at 20% jitter; degrades after (80% at 40%, 40% at 60%, 22% at 80%).
  Jitter % = stdev of Gaussian vertex displacement.
- **Isogroup removal speedup (Table 1)**: full vs cut.
  - Indy: 2s → 0.3s (×8), isogroups 775 → 54 (7%)
  - Barcelona: 131s → 1.5s (×89), 5439 → 338 (6%)
  - Mexico: 2.9k s → 5.0s (×584), 25k → 242 (1%)
  - Cut keeps the most-frequent isogroups; missed ones have <10 repetitions (negligible). Frequency
    distributions of full vs cut differ <1% (Fig 16).
- **Performance (Table 2)**: e.g. Fig 17 = 72k V / 110k E, 67s, 1411 rules; Fig 13 = 6.7k V /
  10.2k E, 704s, 3098 rules.
- **User-guided analysis (Fig 17)**: seed expansion from a user-selected isogroup; much faster
  because larger seed graphs have fewer repetitions. Largest example 110k edges, ~1 min.
- **Terminal replacement (Fig 1)**: Barcelona's regular patterns encoded as a terminal, then a plaza
  subgraph manually substituted in.
- **Stitching (Fig 18)**: Manhattan + Paris encoded with different criteria and stitched together,
  preserving street hierarchy/continuity and style.

---

## 8. Limitations & future work (Section 8)

- Limited to grammars that expand a **single node** into a graph (not arbitrary-graph → graph).
- **Quantization** of vertex expansion makes analysis fast but introduces vertex-coding error that
  amplifies across successive encodings.
- **New-node placement & connection** change the appearance of the new graph.
- **Edge embedding** represents each edge as a straight line segment → problems when distant parts
  connect; other edge representations could improve visual quality.
- Exact-topology matching: visually-similar graphs may be classified as different (Fig 19) — e.g. a
  middle vertex not part of the embedding makes two graphs "visually isomorphic" but currently
  treated as different.
- Future: faster isogroup search (e.g. Cheng et al. 2010); **parametric** production rules; context
  sensitivity / environmental response (Open L-systems); **3D** GGGs; mesh encoding/semantic
  analysis; computer-vision scene analysis.

---

## 9. Implementation implications for THIS toolchain (my synthesis)

Key data structures / modules implied by the paper:

1. **GeometricGraph** — vertices with 2D coords + adjacency; induced-subgraph extraction.
2. **GeometricIsomorphism** — topological iso check + best affine `T` (rotation/scale/translation)
   alignment + tolerance; canonical normalization (expanded vertex at origin, aligned scale/rot).
3. **Isogroup** — a pattern subgraph `S` + list of occurrence locations + per-occurrence embedding
   `Bi` + repetition count.
4. **VertexExpansion** — polar grid pair (candidate-count grid `f(α,d)` + added-area grid),
   score = frequency × area, pick best cell → new vertex; configurable grid resolution (default
   10×12). Convex-hull area computation.
5. **IsogroupDetection loop** — order-by-order expansion; frequency-based pruning (~80% cut, smaller
   early); isomorphism-based merge (after frequency cut); frequency table output.
6. **IsogroupSelection** — pick largest-most-frequent; geometric constraints (aspect ratio, leaves);
   dual-overlap graph + max-clique → largest non-overlapping occurrence set.
7. **GrammarEncoder** — RHS copy (S + embeddings); LHS new-node placement strategy (existing-vertex,
   importance-weighted; pluggable per application); edge-render pruning.
8. **Hierarchical driver** — replace → re-analyze loop building levels; axiom + rule list = grammar.
9. **Forward generator** — turtle-like single-pass interpreter applying rules with local coordinate
   frames `Ti`, relaxed embedding with distance threshold, parallel rule application.
10. **I/O** — OSM import; rendering/decoding for validation.

Open design choices to confirm with the user before building:
- Target language/stack (paper used C++/Boost/Qt). 
- Scope: full forward+inverse, or inverse (learning) only first?
- 2D only (paper) vs planned 3D (future work)?
