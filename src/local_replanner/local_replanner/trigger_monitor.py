"""Trigger detection with explicit priority for local replan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from local_replanner.replan_core import parse_emergency_landing_json

# Priority: lower index = higher priority (evaluated first).
PRIORITY_ORDER = (
    "EMERGENCY",
    "DAIDALUS",
    "GEOFENCE",
    "QUALITY_FL",
    "TRACK_DEVIATION",
)


@dataclass
class TriggerSnapshot:
    emergency_json: str
    daidalus_alert: int
    violation_imminent: bool
    quality_flag: float
    qf_threshold: float
    track_deviation_m: float
    track_threshold_m: float


def emergency_target_active(emergency_json: str) -> bool:
    if not emergency_json.strip():
        return False
    try:
        d = parse_emergency_landing_json(emergency_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    return bool(d.get("reachable")) and "lat" in d and "lon" in d


def select_active_trigger(snap: TriggerSnapshot) -> Optional[str]:
    """Return highest-priority active trigger name, or None if nominal."""
    candidates: List[Tuple[int, str]] = []
    if emergency_target_active(snap.emergency_json):
        candidates.append((PRIORITY_ORDER.index("EMERGENCY"), "EMERGENCY"))
    if snap.daidalus_alert >= 1:
        candidates.append((PRIORITY_ORDER.index("DAIDALUS"), "DAIDALUS"))
    if snap.violation_imminent:
        candidates.append((PRIORITY_ORDER.index("GEOFENCE"), "GEOFENCE"))
    if snap.quality_flag < snap.qf_threshold:
        candidates.append((PRIORITY_ORDER.index("QUALITY_FL"), "QUALITY_FL"))
    if snap.track_deviation_m > snap.track_threshold_m:
        candidates.append((PRIORITY_ORDER.index("TRACK_DEVIATION"), "TRACK_DEVIATION"))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]
