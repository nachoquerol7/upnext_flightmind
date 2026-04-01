"""Flight level assignment from terrain, ceiling, nav quality, and base margin."""

from __future__ import annotations

import math
from typing import Tuple

M_TO_FT = 3.280839895013123


def compute_assigned_fl(
    terrain_max_m: float,
    ceiling_m: float,
    quality_flag: float,
    base_margin_m: float,
) -> Tuple[float, str]:
    """
    Returns (assigned_fl, status).
    FL = pressure-style flight level in hundreds of feet (e.g. 35 -> FL3500 ft AMSL proxy).
    status: OK | HOLD | TERRAIN_INVALID
    """
    if quality_flag < 0.5:
        return float("nan"), "HOLD"
    if math.isnan(terrain_max_m) or math.isinf(terrain_max_m):
        return float("nan"), "TERRAIN_INVALID"
    if ceiling_m <= 0.0:
        return float("nan"), "TERRAIN_INVALID"

    if quality_flag > 0.8:
        margin_ft = 300.0
    else:
        margin_ft = 500.0

    alt_m = terrain_max_m + base_margin_m
    alt_ft = alt_m * M_TO_FT + margin_ft
    fl_raw = alt_ft / 100.0
    ceiling_fl = (ceiling_m * M_TO_FT) / 100.0
    fl = min(fl_raw, ceiling_fl)
    return fl, "OK"
