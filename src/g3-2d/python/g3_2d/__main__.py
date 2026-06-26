"""Package entry point: ``python -m g3_2d <graph.json> -o <out.ggg.json>`` learns a grammar."""

from __future__ import annotations

from .learn import _main

if __name__ == "__main__":
    raise SystemExit(_main())
