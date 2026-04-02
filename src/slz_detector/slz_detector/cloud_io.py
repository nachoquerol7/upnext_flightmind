"""Lectura mínima de xyz desde sensor_msgs/PointCloud2."""

from __future__ import annotations

import math
import struct
from typing import Iterator

from sensor_msgs.msg import PointCloud2


def iter_xyz_points(msg: PointCloud2) -> Iterator[tuple[float, float, float]]:
    ox = oy = oz = None
    for f in msg.fields:
        if f.name == "x":
            ox = int(f.offset)
        elif f.name == "y":
            oy = int(f.offset)
        elif f.name == "z":
            oz = int(f.offset)
    if ox is None or oy is None or oz is None:
        return
    step = int(msg.point_step)
    w = int(msg.width) * int(msg.height)
    data = msg.data
    for i in range(w):
        base = i * step
        if base + max(ox, oy, oz) + 4 > len(data):
            break
        x = struct.unpack_from("<f", data, base + ox)[0]
        y = struct.unpack_from("<f", data, base + oy)[0]
        z = struct.unpack_from("<f", data, base + oz)[0]
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            yield (float(x), float(y), float(z))


def list_xyz_points(msg: PointCloud2) -> list[tuple[float, float, float]]:
    return list(iter_xyz_points(msg))
