"""Clasificador de terreno por geometría de nube (SIL; cámara reservada)."""

from __future__ import annotations

import math
from typing import Any, Sequence


class TerrainClassifier:
    """Puntuación de celda a partir de puntos locales."""

    @staticmethod
    def classify_flatness(points: Sequence[tuple[float, float, float]]) -> float:
        """Desviación típica de Z: terreno plano → varianza baja → score alto [0,1]."""
        if len(points) < 2:
            return 0.0
        zs = [float(p[2]) for p in points]
        mean_z = sum(zs) / len(zs)
        var = sum((z - mean_z) ** 2 for z in zs) / len(zs)
        std = math.sqrt(max(0.0, var))
        return float(min(1.0, 1.0 / (1.0 + 8.0 * std)))

    @staticmethod
    def classify_density(points: Sequence[tuple[float, float, float]], cell_area_m2: float) -> float:
        """Puntos por m² normalizado a [0,1] (ref ~50 pts/m² → 1.0)."""
        if cell_area_m2 <= 0.0 or not points:
            return 0.0
        density = len(points) / float(cell_area_m2)
        return float(min(1.0, density / 50.0))

    def score(self, points: Sequence[tuple[float, float, float]], cell_area_m2: float) -> float:
        """Media ponderada: 0.7 flatness + 0.3 density."""
        f = self.classify_flatness(points)
        d = self.classify_density(points, cell_area_m2)
        return float(0.7 * f + 0.3 * d)

    def classify(self, image: Any) -> float:
        """Reservado para visión; stub fijo."""
        return 0.8
