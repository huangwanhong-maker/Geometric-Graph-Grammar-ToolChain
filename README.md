# Geometric Graph Grammar ToolChain (G³)

An infrastructure and analysis foundation for **geometric grammar induction** — learning
context-free geometric graph grammars from input graphs (inverse procedural modeling) and
generating geometric structures from them (forward modeling).

The algorithm is based on:

> Marek Fiser, Bedrich Benes, Jorge Garcia Galicia, Michel Abdul-Massih, Daniel G. Aliaga,
> Vojtech Krs. **"Learning Geometric Graph Grammars."** SCCG'16, Purdue University.
> ACM DOI: [10.1145/2948628.2948635](http://dx.doi.org/10.1145/2948628.2948635)

A careful walkthrough of the algorithm (with figure analysis) lives in
[docs/ALGORITHM_NOTES.md](docs/ALGORITHM_NOTES.md). The paper itself is in [docs/paper/](docs/paper/).

## What it does

A **Geometric Graph Grammar (GGG)** encodes both *topology* and *2D/3D geometry*. Learning works
like data compression on graphs: find frequently repeated, geometrically-isomorphic subgraphs
("isogroups"), replace each occurrence with a single node, and emit a rewriting rule — repeated
hierarchically to build a compact, generative description of the input.

## Demo (2D Python)

**Forward** — apply a recursive grammar to *generate* a fractal (the paper's Fig. 12 Sierpinski
triangle); **inverse** — feed that fractal back and *induce* a grammar that recovers the recursive
**triangle hierarchy**, color-coding each occurrence.

| Forward: generate the fractal | Inverse: induce its grammar | Inverse on a grid |
|:---:|:---:|:---:|
| ![Sierpinski generated](assets/sierpinski_forward.png) | ![Sierpinski induced](assets/sierp4.png) | ![Grid squares](assets/grid_squares.png) |
| `grammar → graph` | `graph → grammar` (triangles) | repeated unit squares |

```sh
cd src/g3-2d/python
pip install -e ".[dev,viz]"

# forward: generate the Sierpinski triangle
python -m g3_2d.examples sierpinski -n 6 -o sierpinski.png

# round-trip: induce a recursive triangle grammar back from a generated fractal
python -c "from g3_2d.examples import sierpinski; from g3_2d.forward import generate; \
from g3_2d.io import save_json; save_json(generate(sierpinski(),4),'sierp4.json')"
python -m g3_2d sierp4.json -o sierp4.ggg.json --draw sierp4.png --max-order 3 --prefer dense
```

The induction prints an analysis report (isogroup counts, per-rule table, compression %), writes the
grammar as `*.ggg.json` (rules `q → S / B` plus the world occurrences of each rule), and draws the
occurrences. See [src/g3-2d/python/README.md](src/g3-2d/python/README.md) for all options.

## Repository layout

```
docs/                     Paper + algorithm notes (the conceptual reference)
src/
  g3-2d/                  2D geometric graph grammars
    python/               Python implementation   ← current focus
    cpp/                  C++ implementation
  g3-3d/                  3D geometric graph grammars
    python/               Python implementation
    cpp/                  C++ implementation
LICENSE                   MIT (© Serendip Commons Society)
CONTRIBUTORS.md           Contributor list
```

There are four parallel implementations (2D/3D × Python/C++). The 2D dimension is being designed
and built first, beginning with the Python implementation; the others follow.

## Status

- **2D Python** — functional end to end: forward generation (fractals) and inverse learning
  (detection → selection → encoding → hierarchical rewriting), with analysis reports and
  visualization. See [src/g3-2d/python/README.md](src/g3-2d/python/README.md).
- **2D C++, 3D Python, 3D C++** — planned; the 2D-Python module and shared `fixtures/` are the
  specification they validate against.

## License

[MIT](LICENSE) — Copyright © 2026 Serendip Commons Society. See [CONTRIBUTORS.md](CONTRIBUTORS.md).
