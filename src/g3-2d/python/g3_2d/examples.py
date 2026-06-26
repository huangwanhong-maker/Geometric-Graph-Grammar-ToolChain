"""Example forward grammars, including the recursive Sierpinski triangle (paper Fig. 12)."""

from __future__ import annotations

import numpy as np

from .forward import ForwardGrammar, Production
from .geometry import Similarity
from .graph import GeometricGraph

_H = float(np.sqrt(3) / 2)  # height of a unit equilateral triangle


def _unit_triangle() -> GeometricGraph:
    g = GeometricGraph()
    g.add_vertex(0, (0.0, 0.0))
    g.add_vertex(1, (1.0, 0.0))
    g.add_vertex(2, (0.5, _H))
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 0)
    return g


def sierpinski() -> ForwardGrammar:
    """The Sierpinski triangle: one symbol ``S`` whose triangle splits into three half-scale copies.

    Each derivation step replaces a triangle with the three corner sub-triangles (the middle one is
    left empty); composing the half-scale similarities across levels yields the classic fractal.
    """
    g0 = Similarity.from_components(scale=0.5)                      # bottom-left corner
    g1 = Similarity.from_components(scale=0.5, tx=0.5)              # bottom-right corner
    g2 = Similarity.from_components(scale=0.5, tx=0.25, ty=_H / 2)  # top corner
    return ForwardGrammar(
        axiom=[("S", Similarity.identity())],
        productions={"S": Production("S", [("S", g0), ("S", g1), ("S", g2)])},
        terminals={"S": _unit_triangle()},
    )


EXAMPLES = {"sierpinski": sierpinski}


def _main(argv: list[str] | None = None) -> int:
    import argparse

    from .forward import generate

    parser = argparse.ArgumentParser(description="Render an example forward (fractal) grammar.")
    parser.add_argument("example", choices=sorted(EXAMPLES))
    parser.add_argument("-n", "--iterations", type=int, default=6)
    parser.add_argument("-o", "--out", help="output PNG (needs the 'viz' extra)")
    args = parser.parse_args(argv)

    g = generate(EXAMPLES[args.example](), args.iterations)
    print(f"{args.example} (n={args.iterations}): {g.num_vertices} vertices, {g.num_edges} edges")
    if args.out:
        from .viz import save_png
        save_png(g, args.out, node_size=2.0)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
