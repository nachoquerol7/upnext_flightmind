"""EventLogger unit tests."""

from __future__ import annotations

import json
from pathlib import Path

from flightmind_common.event_logger import EventLogger


def test_event_logger_writes_jsonl(tmp_path: Path) -> None:
    log = EventLogger(log_dir=str(tmp_path), flush_interval_s=0.0)
    log.log_transition("A", "B", "t", {"x": True})
    log.close()
    files = list(tmp_path.glob("mission_*.jsonl"))
    assert len(files) == 1
    line = files[0].read_text(encoding="utf-8").strip().splitlines()[0]
    obj = json.loads(line)
    assert obj["type"] == "fsm_transition"
    assert obj["to"] == "B"
