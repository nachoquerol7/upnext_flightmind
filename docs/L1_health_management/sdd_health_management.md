 sdd_health_management.md

**Document ID:** FM-SDD-L2.4  
**Version:** 1.0  
**Date:** 2026-04-02  
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext Spain  
**Status:** Draft

---

## 1. Purpose

This domain monitors the health of the aircraft system itself — sensors, actuators, communication links, and software nodes. It detects faults, classifies them by severity, and publishes contingency commands to the Mission FSM. It is the last line of defence before an autonomous emergency response.

---

## 2. Domain Decomposition

```
L2.4 — Health Management
├── fdir               (pkg: fdir — fdir_node.py + fdir_core.py)
│   └── watchdog       (pkg: fdir — watchdog_node.py, XFAIL)
├── c2_monitor         (pkg: fdir — c2_monitor_node.py + c2_monitor.py)
└── battery_monitor    (pkg: fdir — battery_monitor_node.py + battery_monitor.py)
```

**Why one package, four nodes:** All health management functions share the same config file (`fdir.yaml`), the same severity table (`fdir_severity.yaml`), and the same output pattern — a fault atom to the FSM. Splitting into separate packages would create unnecessary build complexity without functional benefit.

**watchdog is internal to fdir** — it monitors ROS2 node heartbeats and publishes `safe_mode`. It is architecturally separate from fault detection but lives in the same package. Currently XFAIL (ARCH-1.7-WATCHDOG).

---

## 3. Subsystem: fdir

### 3.1 Function

Evaluates a snapshot of system state every 50ms (20 Hz) and applies the severity/action table to determine if a fault condition exists and what the system response should be. Publishes fault identity, policy action, and emergency landing target.

### 3.2 Implementation

- **ROS2 node:** `src/fdir/fdir/fdir_node.py` — `FdirNode`
- **Core engine:** `src/fdir/fdir/fdir_core.py` — `FdirEngine`, `FdirSnapshot`
- **Severity table:** `src/fdir/fdir/severity_table.py`
- **Config:** `src/fdir/config/fdir.yaml`, `src/fdir/config/fdir_severity.yaml`

### 3.3 Fault detection logic

The `FdirEngine.evaluate(snap)` method receives a `FdirSnapshot` every tick and checks four fault detectors:

**Navigation quality detector:**
```python
# From fdir_core.py — quality thresholds from fdir.yaml
nav_mild_below:     0.65  → fault: NAV_MILD
nav_severe_below:   0.35  → fault: NAV_SEVERE
nav_critical_below: 0.15  → fault: NAV_CRITICAL (→ ABORT)
# quality_flag = 0.0 if no odometry for > sensor_timeout_nav_quality_s (3.0s)
```

**Motor loss detector:**
Detects thrust/acceleration mismatch — high throttle command with downward (negative) vertical acceleration:
```python
# Conditions (all must hold for motor_loss_window_s = 2.0s):
throttle_commanded > motor_loss_throttle_min   # 0.35
vertical_accel_m_s2 < motor_loss_vertical_accel_max_m_s2  # -1.5 m/s²
armed == True
# If sustained → fault: MOTOR_DEGRADED → severity: HIGH → action: RTB
```

**C2 link detector:**
```python
# c2_heartbeat_last_rx updated by /fdir/in/c2_heartbeat (any Bool message)
elapsed = now - c2_heartbeat_last_rx
if elapsed > c2_heartbeat_timeout_s:  # 1.5s
    → fault: C2_LOST → severity: HIGH → action: RTB
```

**Sensor timeout detector:**
```python
# quality_flag source timeout
if (now - last_quality_rx_time) > sensor_timeout_nav_quality_s:  # 3.0s
    quality_flag = 0.0  → triggers NAV_CRITICAL
```

### 3.4 Severity and action table

Full table from `fdir_severity.yaml`:

| Fault | Severity | Action |
|---|---|---|
| IMU_FAILED | CRITICAL | ABORT |
| THERMAL_CRITICAL | CRITICAL | ABORT |
| GPS_FAILED | HIGH | RTB |
| BARO_FAILED | HIGH | RTB |
| MOTOR_DEGRADED | HIGH | RTB |
| BATTERY_CRITICAL | HIGH | RTB |
| C2_LOST | HIGH | RTB |
| BATTERY_LOW | MEDIUM | RTB |
| GCS_LOST | MEDIUM | RTB |
| LIDAR_FAILED | MEDIUM | DEGRADE |

**CRITICAL → `fdir_emergency=True`** published synchronously on `/fdir/in/fdir_emergency`. The FSM reacts on the next tick — guaranteed < 50ms (20Hz FSM tick) + < 50ms (20Hz FDIR tick) = < 100ms end-to-end from fault to FSM state change.

**HIGH → `rtb_command=True`** published on `/fsm/in/rtb_command`.

**MEDIUM → DEGRADE** — reduces quality_flag contribution, no FSM command.

### 3.5 Emergency landing target selection

FDIR maintains a list of pre-configured emergency landing zones ranked by runway length and surface quality. On each tick it computes which zones are reachable given current altitude and glide ratio:

```python
# Glide reachability
horizontal_reach_m = glide_ratio * vehicle_altitude_amsl_m
# Default: glide_ratio=18, altitude=2000m → reach=36km
```

Zones within reach are ranked by `quality` score. The best reachable zone is published as JSON on `/fdir/emergency_landing_target`.

```yaml
# fdir.yaml — pre-configured zones
emergency_landing_zones:
  - lat: 40.05  lon: -3.02  longitud_pista: 900   calidad: 0.95
  - lat: 40.50  lon: -3.50  longitud_pista: 1200  calidad: 0.85
  - lat: 41.20  lon: -2.00  longitud_pista: 800   calidad: 0.70
```

These static zones are complemented dynamically by the `landing_zone_detector` output (`/slz/best`) — the FSM `slz_available` atom checks for a fresh, high-scoring SLZ candidate before allowing `ABORT→LANDING`.

### 3.6 C2 loss contingency sequence

FDIR implements the full EU 2019/947 Annex III C2 loss procedure:

```
C2 heartbeat lost (c2_heartbeat_timeout_s = 1.5s)
  │
  ├─ link_loss_hold_s  = 30s  → maintain current heading and altitude
  ├─ link_loss_rtb_s   = 30s  → initiate RTB (publish rtb_command)
  └─ link_loss_land_s  = 120s → emergency landing at nearest zone
```

### 3.7 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/nav/quality_flag` | `std_msgs/Float64` | navigation_bridge |
| `/fsm/current_mode` | `std_msgs/String` | mission_fsm |
| `/fdir/in/c2_heartbeat` | `std_msgs/Bool` | GCS / c2_monitor |
| `/fmu/out/vehicle_imu` | `px4_msgs/VehicleImu` | PX4 |
| `/fmu/out/vehicle_status` | `px4_msgs/VehicleStatus` | PX4 |
| `/fmu/out/vehicle_attitude_setpoint` | `px4_msgs/VehicleAttitudeSetpoint` | PX4 |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/fdir/active_fault` | `std_msgs/String` | 20 Hz |
| `/fdir/policy_action` | `std_msgs/String` | 20 Hz |
| `/fdir/emergency_landing_target` | `std_msgs/String` (JSON) | 20 Hz |

**FSM atoms published (via `/fsm/in/` topics):**

| Atom | Topic | Condition |
|---|---|---|
| `fdir_emergency` | `/fsm/in/fdir_emergency` | CRITICAL severity |
| `rtb_command` | `/fsm/in/rtb_command` | HIGH severity |

### 3.8 Configuration

```yaml
# fdir.yaml — key parameters
nav_mild_below:                0.65
nav_severe_below:              0.35
nav_critical_below:            0.15
motor_loss_window_s:           2.0
motor_loss_throttle_min:       0.35
motor_loss_vertical_accel_max_m_s2: -1.5
sensor_timeout_nav_quality_s:  3.0
c2_heartbeat_timeout_s:        1.5
link_loss_hold_s:              30.0
link_loss_rtb_s:               30.0
link_loss_land_s:              120.0
glide_ratio:                   18.0
```

### 3.9 V&V status

- **22 passed**, 2 xfail (watchdog), 0 failed
- Test suites: `test_fdir_phase3.py`, `test_severity_table.py`, `test_c2_monitor.py`, `test_battery_monitor.py`
- Integrated into mission_fsm m6 and m10 suites
- `test_tc_fsm_009_event_to_abort` — demo suite ✓
- Open: `ARCH-FDIR-SEV` — severity table not versioned, combination faults not modelled

---

## 4. Subsystem: watchdog

### 4.1 Function

Monitors heartbeat topics from critical ROS2 nodes (mission_fsm, navigation_bridge, DAIDALUS). If a node stops publishing its heartbeat, publishes `safe_mode=True`.

### 4.2 Implementation

- **Node:** `src/fdir/fdir/watchdog_node.py`
- **Status:** XFAIL — `watchdog_node.py` exists but is not fully implemented

### 4.3 Open gap

**ARCH-1.7-WATCHDOG:** The watchdog node is a stub. It imports correctly and can be launched, but the heartbeat monitoring logic is not wired to the FSM. TC-FDIR-007, TC-FDIR-008, TC-MW-001, TC-FAULT-008 are XFAIL with reason `XFAIL-ARCH-1.7-WATCHDOG: watchdog_node not implemented`.

This is a HIL blocker — a node crash in CRUISE without watchdog response is an undetected failure mode.

---

## 5. Subsystem: c2_monitor

### 5.1 Function

Dedicated monitor for the Command and Control (C2) link. Tracks MAVLink heartbeat freshness and publishes link status to FDIR and the FSM.

### 5.2 Implementation

- **Node:** `src/fdir/fdir/c2_monitor_node.py`
- **Core:** `src/fdir/fdir/c2_monitor.py`

### 5.3 Logic

```python
# c2_monitor.py
# Subscribes to /c2_link_status (Bool from GCS)
# Tracks time since last True message
# Publishes to /fdir/in/c2_heartbeat when link active
# FDIR c2_heartbeat_timeout_s = 1.5s triggers C2_LOST fault
```

### 5.4 V&V status

- `test_c2_monitor.py` passing
- Integrated into FSM supervision via `c2_lost` atom in `mission_fsm_node.py`

---

## 6. Subsystem: battery_monitor

### 6.1 Function

Monitors battery percentage from PX4 (`/battery_state`) and publishes `battery_low` and `battery_critical` atoms to the FSM with a sustain timer to avoid false positives from momentary voltage sag.

### 6.2 Implementation

- **Node:** `src/fdir/fdir/battery_monitor_node.py`
- **Core:** `src/fdir/fdir/battery_monitor.py`

### 6.3 Logic

```python
# battery_monitor.py
# Thresholds (from mission_fsm_node.py parameters):
battery_low_threshold:    0.15   # 15% → battery_low atom
battery_low_sustain_sec:  2.0    # must persist for 2s before triggering
# battery_critical is a separate atom — immediate, no sustain
```

The sustain timer prevents a brief voltage transient during high-power manoeuvres from triggering an RTB. The CRITICAL threshold triggers ABORT immediately (no sustain) — a conservative choice for a safety-critical event.

### 6.4 V&V status

- `test_battery_monitor.py` passing
- Integrated into FSM m13 safety atoms suite

---

## 7. Design Decisions and Rationale

### 7.1 Why 20 Hz evaluation rate

FDIR must detect a fault and publish `fdir_emergency` within 500ms P99 (requirement FDIR-021). At 20 Hz (50ms per tick), the worst-case detection latency is one tick (50ms) plus one FSM tick (50ms at 20 Hz) = 100ms — well within the 500ms budget. A lower rate would risk missing fast-onset faults (e.g. motor failure during takeoff).

### 7.2 Why sustain timers on battery_low but not on CRITICAL

`battery_low` (15%) is a precautionary threshold — a brief sag during a turn should not trigger RTB. The 2-second sustain filter prevents transients from causing unnecessary contingency responses.

`battery_critical` has no sustain — at critical battery levels, any delay in response is itself a safety risk. The asymmetry is intentional.

### 7.3 Why static emergency landing zones + dynamic SLZ

Static zones provide a guaranteed fallback — they are always available regardless of sensor state. Dynamic SLZ detection via the `landing_zone_detector` provides better options when sensors are functional, but the system must not depend on neural network inference for emergency response. The FSM uses `slz_available` as an *enhancement* of the ABORT→LANDING transition, not a precondition.

### 7.4 Why C2 loss is in Health Management, not Collision Avoidance

C2 loss is a **system contingency** — a failure of system infrastructure — not an external threat. FDIR handles infrastructure failures; Collision Avoidance handles external threats. The contingency procedure (hold → RTB → land) is analogous to a sensor timeout response, not a traffic conflict response.

---

## 8. Known Limitations and Open Gaps

| Gap | Description | Impact |
|---|---|---|
| ARCH-1.7-WATCHDOG | watchdog_node not implemented | Node crashes undetected — HIL blocker |
| ARCH-FDIR-SEV | Severity table not versioned, multiple simultaneous faults not modelled | Undefined behaviour for combined faults |
| FDIR-014 | Severity table as external YAML not fully wired | Manual config required per deployment |
| Static LZ | Emergency landing zones are hardcoded lat/lon | Not portable across operating environments |

---

## 9. References

- `src/fdir/fdir/fdir_node.py`
- `src/fdir/fdir/fdir_core.py`
- `src/fdir/fdir/severity_table.py`
- `src/fdir/fdir/watchdog_node.py`
- `src/fdir/fdir/c2_monitor_node.py`
- `src/fdir/fdir/battery_monitor_node.py`
- `src/fdir/config/fdir.yaml`
- `src/fdir/config/fdir_severity.yaml`
- `src/mission_fsm/docs/vnv/XFAIL_INDEX.md` — ARCH-1.7-WATCHDOG
