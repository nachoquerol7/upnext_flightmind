"""Structured JSONL event log (FSM-073, DAA-066, ARCH-1.10)."""

from __future__ import annotations

import json
import pathlib
import time
from typing import Any, Dict, List, Mapping, Optional


class EventLogger:
    """Append-only JSONL with periodic flush."""

    def __init__(self, log_dir: str = "/tmp/flightmind_logs", flush_interval_s: float = 1.0) -> None:
        self.log_dir = pathlib.Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = int(time.time())
        self.log_file = self.log_dir / f"mission_{self.session_id}.jsonl"
        self._buffer: List[str] = []
        self._last_flush = time.time()
        self.flush_interval_s = flush_interval_s

    def log_transition(
        self, from_state: str, to_state: str, trigger: str, atoms_active: Optional[Mapping[str, Any]] = None
    ) -> None:
        self._write(
            {
                "type": "fsm_transition",
                "ts_ns": time.time_ns(),
                "from": from_state,
                "to": to_state,
                "trigger": trigger,
                "atoms": dict(atoms_active) if atoms_active else {},
            }
        )

    def log_daa_alert(
        self, prev_level: int, new_level: int, intruder_id: str, hmd_m: float, ttv_s: float
    ) -> None:
        self._write(
            {
                "type": "daa_alert",
                "ts_ns": time.time_ns(),
                "prev": prev_level,
                "new": new_level,
                "intruder": intruder_id,
                "hmd_m": hmd_m,
                "ttv_s": ttv_s,
            }
        )

    def log_fault(self, fault_name: str, severity: str, action: str) -> None:
        self._write(
            {
                "type": "fault",
                "ts_ns": time.time_ns(),
                "fault": fault_name,
                "severity": severity,
                "action": action,
            }
        )

    def _write(self, event: Dict[str, Any]) -> None:
        self._buffer.append(json.dumps(event))
        if (time.time() - self._last_flush) >= self.flush_interval_s:
            self._flush()

    def _flush(self) -> None:
        if not self._buffer:
            self._last_flush = time.time()
            return
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write("\n".join(self._buffer) + "\n")
        self._buffer.clear()
        self._last_flush = time.time()

    def close(self) -> None:
        self._flush()
