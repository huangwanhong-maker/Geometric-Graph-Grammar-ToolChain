# Idea: 2-complex-based induction & dimensional reduction of m-D grammars

> **Status:** conjecture / future work. NOT implemented. We implement the paper's graph-based
> algorithm first (see [../ALGORITHM_NOTES.md](../ALGORITHM_NOTES.md)).
> **Origin:** Wanhong HUANG, 2026-06-26.

## The seed idea (as stated)

> "One possible algorithm for the high-dimensional condition is that m-D can in fact reduce to a 2D
> problem. A (k+1)-complex can be obtained from (k)-complexes. The initial 2D algorithm then differs
> from the paper — our new idea is **2-complex-based induction**."

## Restatement

The paper operates on a **geometric graph**, which is a **1-dimensional simplicial complex**:
0-simplices = vertices, 1-simplices = edges. Its induction primitive is the **edge**, grown by
**vertex expansion**, and its repeated patterns ("isogroups") are repeated *subgraphs*.

The proposal generalizes the object and the induction primitive:

- **Object:** a geometric **simplicial complex** instead of a geometric graph.
  (0-simplex = point, 1-simplex = edge, 2-simplex = triangle/face, 3-simplex = tetrahedron, …;
  a simplicial complex is a set of simplices closed under taking faces, glued along shared faces.)
- **Induction primitive:** the **2-simplex (2-complex / face)** instead of the edge. Pattern
  discovery, expansion, and rewriting all operate on 2-cells and their gluings rather than on
  vertices/edges.
- **Dimensional-reduction conjecture:** induction in dimension *m* reduces to repeated 2D
  sub-problems, because a `(k+1)`-complex is assembled by **gluing `k`-complexes along shared
  `(k−1)`-faces**. Recursively peeling dimensions should let a high-D grammar be expressed through
  lower-dimensional (ultimately 2-complex) induction.

### Combinatorial anchor (to be firmed up)
- The boundary of a single `(k+1)`-simplex consists of `k+2` faces that are themselves `k`-simplices.
- Conversely, gluing `k`-simplices/`k`-complexes along `(k−1)`-faces builds up `(k+1)`-complexes.
- The precise statement of "m-D reduces to 2D" — what is preserved, what is lost, and under what
  conditions the reduction is exact vs. approximate — is the **central open question** of this idea.

## Why this differs from the paper, even in 2D

- **Paper, 2D:** primitives are vertices + edges (1-complex). Expansion adds a *vertex*; the score is
  `frequency × convex-hull area`; patterns are repeated induced *subgraphs*; isomorphism is
  graph-iso + affine alignment.
- **This idea, 2D:** primitives are *faces* (2-simplices). Expansion adds a *2-cell*; the analog of
  "area" might be `k`-content / volume; patterns are repeated *sub-complexes*; isomorphism must
  respect **face incidence**, not just vertex/edge adjacency. So even the 2D algorithm is a different
  algorithm, not a special case of the paper's.

## Why it is attractive

- **Surfaces & meshes fall out naturally.** Triangular meshes ARE 2-complexes; the paper's own
  future-work section explicitly wants GGGs for 3D/triangular meshes and semantic mesh analysis.
  Face-based induction targets that directly.
- **Uniform treatment of dimension.** One induction engine (over `k`-complexes), parameterized by
  dimension, instead of a separate algorithm per dimension.
- **Richer geometric invariants.** Faces/volumes give more discriminative repeated structure than
  edges alone, potentially reducing the false-merge problem (cf. paper Fig. 19, where exact-topology
  matching calls visually-identical graphs different).

## Open questions / what to work out before implementing

1. **Reduction theorem.** State and (dis)prove "m-D induction ≈ iterated 2-complex induction."
   What is the gluing data that must be retained across the reduction?
2. **Complex isomorphism + canonicalization.** Geometric iso over simplicial complexes (incidence-
   preserving + affine/similarity alignment); a canonical normal form analogous to the paper's
   "expanded vertex at origin, aligned scale/rotation."
3. **Expansion primitive & scoring.** What is "vertex expansion" for 2-cells? What replaces
   `frequency × area` (likely `frequency × k-volume`)? What is the discretization analog of the
   paper's polar grid in higher dimension?
4. **Embedding / rewriting.** How does the GGG embedding `B = {(vᵢ, Tᵢ, {pᵢⱼ})}` generalize when a
   single cell (or its dual) is replaced by a sub-complex, and how is relaxed embedding defined on
   faces?
5. **Relation to the paper in 2D.** Are 2-complex induction and edge-based induction equivalent on
   planar graphs, or do they capture genuinely different pattern sets? (Likely the latter.)
6. **Data structures.** This is where the "high flexibility" the project wants for 3D/high-D is
   actually needed — a generic `k`-complex representation, vs. the concrete graph representation that
   suffices for the paper's 2D algorithm.

## Relation to the current build

- The paper's graph (1-complex) algorithm is implemented first, in `src/g3-2d/python/`.
- This idea would eventually live in its own track (a complex-based induction engine), reusing the
  geometry/affine/isomorphism foundations but with a `k`-complex object model. Keep the paper impl's
  interfaces clean enough that a complex-based engine can sit beside them without contortion.
