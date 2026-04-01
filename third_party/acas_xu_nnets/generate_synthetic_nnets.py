#!/usr/bin/env python3
"""Generate minimal SIL .nnet stubs (HEURISTIC_SIL_V1) for acas_node when upstream weights are unavailable."""
from __future__ import annotations

import argparse
import os


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "src", "acas_node", "nnets"),
        help="Output directory (default: src/acas_node/nnets)",
    )
    args = p.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    for i in range(45):
        path = os.path.join(out, f"acas_xu_{i:02d}.nnet")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# SYNTHETIC-NET — replace with real .nnet for production\n")
            f.write("MODE HEURISTIC_SIL_V1\n")
    print(f"Wrote 45 files to {out}")


if __name__ == "__main__":
    main()
