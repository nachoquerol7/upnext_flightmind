"""Load FDIR fault severity / action table from YAML (FDIR-009, FDIR-010)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping

import yaml


def load_severity_table(path: str | Path) -> Dict[str, Dict[str, str]]:
    """Return faults[name] -> {severity, action}."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        root: MutableMapping[str, Any] = yaml.safe_load(f)
    if not isinstance(root, Mapping):
        raise ValueError("severity YAML root must be a mapping")
    faults = root.get("faults")
    if not isinstance(faults, Mapping):
        raise ValueError("severity YAML must contain 'faults' mapping")
    out: Dict[str, Dict[str, str]] = {}
    for name, spec in faults.items():
        if not isinstance(spec, Mapping):
            raise ValueError(f"fault {name!r} must be a mapping")
        sev = spec.get("severity")
        act = spec.get("action")
        if not isinstance(sev, str) or not isinstance(act, str):
            raise ValueError(f"fault {name!r} needs string severity and action")
        out[str(name)] = {"severity": sev, "action": act}
    return out


def lookup_fault(table: Mapping[str, Mapping[str, str]], fault_name: str) -> Mapping[str, str]:
    if fault_name not in table:
        raise KeyError(f"unknown fault: {fault_name!r}")
    return table[fault_name]
