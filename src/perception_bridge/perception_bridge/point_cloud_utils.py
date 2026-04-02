"""Utilidades mínimas para nubes de puntos (stub para FAST-LIO2 / integración)."""

from __future__ import annotations

import math
import struct
from typing import Iterator, Sequence

from sensor_msgs.msg import PointCloud2, PointField

def empty_pointcloud2(frame_id: str = "map") -> PointCloud2:
    """PointCloud2 válido sin puntos (mapa vacío)."""
    msg = PointCloud2()
    msg.header.frame_id = frame_id
    msg.height = 1
    msg.width = 0
    msg.fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = 0
    msg.is_dense = True
    msg.data = bytes()
    return msg


def pointcloud2_from_xyz(
    points: Sequence[tuple[float, float, float]], frame_id: str = "map"
) -> PointCloud2:
    """Construye PointCloud2 desde lista de (x, y, z) en float32."""
    msg = PointCloud2()
    msg.header.frame_id = frame_id
    msg.height = 1
    msg.width = len(points)
    msg.fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = msg.point_step * msg.width
    msg.is_dense = True
    buf = bytearray()
    for x, y, z in points:
        buf.extend(struct.pack("<fff", float(x), float(y), float(z)))
    msg.data = bytes(buf)
    return msg


def iter_xyz_points(msg: PointCloud2) -> Iterator[tuple[float, float, float]]:
    """Itera puntos (x,y,z) float desde PointCloud2 (little-endian, FLOAT32)."""
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
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            continue
        yield (float(x), float(y), float(z))


def list_xyz_points(msg: PointCloud2) -> list[tuple[float, float, float]]:
    return list(iter_xyz_points(msg))


def mean_distance_to_centroid(points: Sequence[tuple[float, float, float]]) -> float:
    """Distancia media euclídea de cada punto al centroide."""
    if not points:
        return float("inf")
    n = len(points)
    cx = sum(p[0] for p in points) / n
    cy = sum(p[1] for p in points) / n
    cz = sum(p[2] for p in points) / n
    return sum(math.dist(p, (cx, cy, cz)) for p in points) / n
