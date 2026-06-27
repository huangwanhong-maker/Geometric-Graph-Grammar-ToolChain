"""Matplotlib visualization for geometric graphs (optional extra).

Not imported by the package core, so the core stays NumPy-only. Install with the ``viz`` extra::

    pip install -e ".[viz]"

CLI::

    python -m g3_2d.viz fixtures/graphs/grid_3x3.json -o grid.png
    python -m g3_2d.viz fixtures/graphs/two_triangles.json --groups 0,1,2 3,4,5 -o tri.png
"""

from __future__ import annotations

from collections.abc import Sequence

from .graph import GeometricGraph

# A colour-blind-friendly cycle for highlighting isogroup occurrences (paper color-codes them).
_PALETTE = [
    "#0072B2", "#E69F00", "#009E73", "#D55E00",
    "#CC79A7", "#56B4E9", "#F0E442", "#999999",
]


def _require_mpl():
    try:
        import matplotlib.pyplot as plt  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - exercised only without matplotlib
        raise ImportError(
            "visualization needs matplotlib; install it with: pip install -e \".[viz]\""
        ) from exc
    return plt


def draw_graph(
    g: GeometricGraph,
    ax=None,
    *,
    groups: Sequence[set[int]] | None = None,
    node_size: float = 40.0,
    base_color: str = "#bbbbbb",
    label_nodes: bool = False,
):
    """Draw ``g`` onto a matplotlib axis.

    ``groups`` optionally colours disjoint vertex sets (e.g. isogroup occurrences) distinctly;
    vertices/edges not in any group are drawn in ``base_color``.
    """
    plt = _require_mpl()
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))

    color_of: dict[int, str] = {}
    for i, grp in enumerate(groups or []):
        for v in grp:
            color_of[v] = _PALETTE[i % len(_PALETTE)]

    # edges first (so nodes draw on top)
    for u, v in g.edges():
        pu, pv = g.position(u), g.position(v)
        same = color_of.get(u) == color_of.get(v) and u in color_of
        ax.plot(
            [pu[0], pv[0]], [pu[1], pv[1]],
            color=color_of[u] if same else base_color,
            linewidth=1.8 if same else 1.0, zorder=1,
        )

    for v in g.vertices():
        p = g.position(v)
        ax.scatter(
            [p[0]], [p[1]], s=node_size,
            color=color_of.get(v, base_color), zorder=2, edgecolors="white", linewidths=0.5,
        )
        if label_nodes:
            ax.annotate(str(v), (p[0], p[1]), textcoords="offset points", xytext=(4, 4), fontsize=8)

    # Explicit, padded limits so even a single node (e.g. a fully-reduced axiom) stays visible;
    # a lone point or a collinear set has zero extent and would otherwise render blank.
    if g.num_vertices:
        pts = g.positions(g.vertices())
        (xmin, ymin), (xmax, ymax) = pts.min(axis=0), pts.max(axis=0)
        span = max(xmax - xmin, ymax - ymin)
        pad = 0.1 * span if span > 0 else 1.0
        ax.set_xlim(xmin - pad, xmax + pad)
        ax.set_ylim(ymin - pad, ymax + pad)

    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def save_png(g: GeometricGraph, path: str, **kwargs) -> None:
    plt = _require_mpl()
    ax = draw_graph(g, **kwargs)
    ax.figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(ax.figure)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    from .io import load_json

    parser = argparse.ArgumentParser(description="Visualize a geometric graph from JSON.")
    parser.add_argument("graph", help="path to a graph JSON file")
    parser.add_argument("-o", "--out", help="output PNG path (omit to show interactively)")
    parser.add_argument("--labels", action="store_true", help="annotate vertex ids")
    parser.add_argument("--node-size", type=float, default=40.0,
                        help="vertex marker size (use ~4 for large/dense maps)")
    parser.add_argument(
        "--groups", nargs="*", default=None,
        help="space-separated vertex groups, each comma-separated, e.g. 0,1,2 3,4,5",
    )
    args = parser.parse_args(argv)

    g = load_json(args.graph)
    groups = (
        [set(int(x) for x in grp.split(",")) for grp in args.groups]
        if args.groups else None
    )
    if args.out:
        save_png(g, args.out, groups=groups, label_nodes=args.labels, node_size=args.node_size)
        print(f"wrote {args.out}")
    else:
        plt = _require_mpl()
        draw_graph(g, groups=groups, label_nodes=args.labels, node_size=args.node_size)
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
