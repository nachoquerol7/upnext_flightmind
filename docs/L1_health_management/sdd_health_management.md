# Health Management — System Design Description
**FM-SDD-04 · v1.0 · 2026-04-02**
**Status:** active
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext

---

## 1. Purpose

Detects sensor and system faults via timeout and physical range checks. Publishes fault events with severity classification and triggers ABORT via `fdir_emergency` within 500ms P99. Manages C2 link contingency per EU 2019/947 Annex III.

---

## 2. BDD [L1 → L2]

```
Health Management [L1]
  + goal: fault detection · isolation · recovery
  + std: ARP4754A §6
  │
  ├── L2: fdir              (pkg: fdir)
  │     + 4 severity levels · 6 detectors · 20Hz · <500ms P99
  │     + 22 passed
  │
  ├── L2: watchdog          (internal to fdir)
  │     + node heartbeat monitoring
  │     + XFAIL ARCH-1.7-WATCHDOG
  │
  ├── L2: c2_monitor        (pkg: fdir/c2_monitor_node.py)
  │     + EU 2019/947 contingency sequence
  │     + hold → RTB → land
  │
  └── L2: battery_monitor   (pkg: fdir/battery_monitor_node.py)
        + fuel/battery threshold monitoring
        + battery_low · battery_critical atoms
```

---

## 3. FDIR Fault Detectors

| Detector | Trigger | Fault name | Threshold |
|---|---|---|---|
| Navigation quality — mild | `quality_flag < 0.65` | NAV_MILD | nav_mild_below = 0.65 |
| Navigation quality — severe | `quality_flag < 0.35` | NAV_SEVERE | nav_severe_below = 0.35 |
| Navigation quality — critical | `quality_flag < 0.15` | NAV_CRITICAL | nav_critical_below = 0.15 |
| Motor loss | High throttle + negative vert accel sustained | MOTOR_DEGRADED | motor_loss_window_s = 2.0s |
| Sensor timeout | No quality_flag for 3.0s | NAV_CRITICAL | sensor_timeout_nav_quality_s = 3.0s |
| C2 loss | No heartbeat for 1.5s | C2_LOST | c2_heartbeat_timeout_s = 1.5s |

### Publications

| Topic | Type | Description |
|---|---|---|
| `/fdir/emergency` | `std_msgs/Bool` | True when CRITICAL fault detected — drives FSM fdir_emergency atom |
| `/fdir/active_fault` | `std_msgs/String` | Current active fault name |
| `/fdir/summary` | `std_msgs/String` (JSON) | Full fault state summary |

---

## 4. Fault Severity Table (fdir_severity.yaml)

| Fault | Severity | Action | FSM atom |
|---|---|---|---|
| IMU_FAILED | CRITICAL | ABORT | `fdir_emergency` |
| THERMAL_CRITICAL | CRITICAL | ABORT | `fdir_emergency` |
| GPS_FAILED | HIGH | RTB | `rtb_command` |
| BARO_FAILED | HIGH | RTB | `rtb_command` |
| MOTOR_DEGRADED | HIGH | RTB | `rtb_command` |
| BATTERY_CRITICAL | HIGH | RTB | `rtb_command` |
| C2_LOST | HIGH | RTB | `rtb_command` |
| BATTERY_LOW | MEDIUM | RTB | `rtb_command` |
| GCS_LOST | MEDIUM | RTB | `rtb_command` |
| LIDAR_FAILED | MEDIUM | DEGRADE | — |

### Fault Response Policy

| Severity | Latency | Action |
|---|---|---|
| LOW | < 1s | Log INFO · add to active_faults |
| MEDIUM | < 500ms | Reduce quality_flag → FSM EVENT |
| HIGH | < 500ms | Publish rtb_command=True |
| CRITICAL | < 100ms | Publish fdir_emergency=True (synchronous) |

---

## 5. C2 Loss Contingency (EU 2019/947 Annex III)

```
C2 link lost (c2_heartbeat_timeout_s = 1.5s)
     │
     ▼
Hold position    (link_loss_hold_s  = 30s)
     │
     ▼
RTB              (link_loss_rtb_s   = 30s)
     │
     ▼
Land immediately (link_loss_land_s  = 120s)
```

FSM transition sequence: CRUISE → RTB (via `c2_lost` atom) → LANDING.

---

## 6. Emergency Landing Zones (fdir.yaml)

Static fallback LZs independent of SLZ detector:

```yaml
emergency_landing_zones:
  - lat: 40.05  lon: -3.02  runway_m: 900   quality: 0.95
  - lat: 40.50  lon: -3.50  runway_m: 1200  quality: 0.85
  - lat: 41.20  lon: -2.00  runway_m: 800   quality: 0.70
# Reachability = glide_ratio (18) × altitude_AMSL_m
```

> Static LZ = guaranteed fallback. Dynamic SLZ = enhancement, not dependency.

---

## 7. Watchdog (XFAIL ARCH-1.7-WATCHDOG)

**Status:** Not implemented — open gap.

**Planned behaviour:**
- Monitor heartbeat topics for: mission_fsm · gpp · navigation_bridge · daidalus · acas_node
- If any node misses heartbeat for > timeout: publish `/fdir/safe_mode` + escalate to fdir_emergency
- Must be < 100 lines active code (TC-FDIR-016 will verify)
- Paradox: watchdog must be simpler than the nodes it monitors

**Affected tests:** TC-FDIR-007, TC-FDIR-008, TC-MW-001, TC-FAULT-008

---

## 8. Key Requirements

| ID | Description | Status |
|---|---|---|
| FDIR-020 | CRITICAL policy: fdir_emergency=True published synchronously | CUBIERTO |
| FDIR-021 | Detection to publication < 500ms P99 | CUBIERTO |
| FDIR-026 | No false positives in 30s nominal operation | CUBIERTO |
| FDIR-023 | fdir_emergency requires explicit operator reset | CUBIERTO |
| FDIR-014 | 4 severity levels in external YAML table | XFAIL ARCH-FDIR-SEV |
| FDIR-029 | External watchdog monitoring FSM/DAA/Nav heartbeats | XFAIL ARCH-1.7-WATCHDOG |

---

## 9. Test Coverage

- **22 passed · 0 xfailed · 0 failed**
- Key tests: emergency flag published, reset mechanism, active_fault not empty, detection latency < 500ms

---

## 10. Open Gaps

| ID | Description | HIL blocker |
|---|---|---|
| ARCH-1.7-WATCHDOG | watchdog_node not implemented | Yes |
| ARCH-FDIR-SEV | Severity table not versioned, combined faults not modelled | No |
