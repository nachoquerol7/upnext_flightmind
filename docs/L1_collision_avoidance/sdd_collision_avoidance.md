# sdd_collision_avoidance.md

**Document ID:** FM-SDD-L2.3  
**Version:** 1.0  
**Date:** 2026-04-02  
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext Spain  
**Status:** Draft

---

## 1. Purpose

This domain detects and resolves threats to flight safety originating from the external environment: air traffic conflicts, airspace violations, and terrain proximity. It operates reactively and independently of mission planning — its outputs are atoms consumed by the Mission FSM regardless of current mission state.

---

## 2. Domain Decomposition

```
L2.3 — Collision Avoidance
├── DAIDALUS           (pkg: upnext_icarous_daa + upnext_icarous_bridge)
├── ACAS Xu            (pkg: acas_node — C++)
├── local_replanner    (pkg: local_replanner)
│   └── emergency_planner  (internal logic)
└── airspace_monitor   (pkg: upnext_airspace + polycarp_node)
```

**Why these four together:** All four respond to external threats with short reaction times (< 100ms to FSM). They share the same input — `NavigationState` and traffic data — and their outputs feed the same consumer: the Mission FSM EVENT and ABORT transitions. Separating them would obscure the unified threat response logic.

**Rejected alternative — DAA and geofence as separate domains:** DAIDALUS handles traffic conflicts; PolyCARP handles airspace containment. Both produce the same type of output — a boolean threat signal with time-to-violation — and both trigger the same FSM atom (`EVENT` or `ABORT`). They belong together.

---

## 3. Subsystem: DAIDALUS

### 3.1 Function

Implements the Well-Clear volume concept from DO-365. Monitors all traffic intruders, computes alert levels, and publishes heading/groundspeed/vertical speed bands indicating which manoeuvres are safe.

### 3.2 Implementation

- **DAA engine:** NASA DAIDALUS v2 (`libTrafficMonitor.so`)
- **ROS2 bridge:** `src/upnext_icarous_bridge/upnext_icarous_bridge/bridge_node.py`
- **Launch:** `src/upnext_icarous_daa/launch/daa_stack.launch.py`

### 3.3 Alert levels

| Level | Name | Meaning | FSM atom |
|---|---|---|---|
| 0 | NONE | No conflict | — |
| 1 | FAR | Preventive — conflict possible | Hysteresis count starts |
| 2 | MID | Corrective — conflict likely | `daidalus_escalated` → EVENT (after 2 ticks) |
| 3 | NEAR | Warning — conflict imminent | `daidalus_near` → EVENT immediately (no hysteresis) |
| 4 | RECOVERY | Post-conflict | `daidalus_recovery` → allows return to CRUISE |

The fast-path for level 3 (NEAR) bypasses the `daidalus_escalate_ticks` hysteresis entirely. This is a deliberate safety decision: NEAR conflicts require immediate response, not debouncing.

### 3.4 Resolution bands

DAIDALUS publishes continuous resolution bands on `/daidalus/bands`:

```
DaidalusBands:
  heading_bands_deg[]     # conflict sectors — avoid these headings
  gs_bands_ms[]           # conflict groundspeed ranges
  vs_bands_ms[]           # conflict vertical speed ranges
  recommended_heading_deg # nearest conflict-free heading
  recommended_gs_ms
  recommended_vs_ms
```

The `local_replanner` consumes these bands to compute an evasion heading.

### 3.5 Feed loss detection

The FSM monitors DAIDALUS message freshness:
```python
# From mission_fsm_node.py
if self._last_daidalus_msg_time is None:
    self._inputs["daidalus_feed_lost"] = False
else:
    self._inputs["daidalus_feed_lost"] = \
        (now - self._last_daidalus_msg_time) > daidalus_feed_timeout_sec  # default 2.0s
```
A DAIDALUS feed loss in CRUISE triggers an EVENT transition — conservative response when DAA awareness is lost.

### 3.6 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/traffic/intruders` | `flightmind_msgs/TrafficReport` | ADS-B receiver |
| `/navigation/state` | `flightmind_msgs/NavigationState` | navigation_bridge |
| `/ownship/state` | `std_msgs/Float64MultiArray` | navigation_bridge |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/daidalus/alert` | `flightmind_msgs/DaidalusAlert` | 10 Hz |
| `/daidalus/alert_level` | `std_msgs/Int32` | 10 Hz |
| `/daidalus/bands` | `flightmind_msgs/DaidalusBands` | 10 Hz |

### 3.7 Message definitions

```
DaidalusAlert:
  header
  int32 alert_level             # 0=NONE 1=FAR 2=MID 3=NEAR 4=RECOVERY
  float64 time_to_violation_s   # -1 if no violation predicted
  float64 min_horizontal_dist_m
  float64 min_vertical_dist_m
  int32 num_conflict_traffic

DaidalusBands:
  header
  float64[] heading_bands_deg   # [from1, to1, from2, to2, ...]
  float64[] gs_bands_ms
  float64[] vs_bands_ms
  float64 recommended_heading_deg
  float64 recommended_gs_ms
  float64 recommended_vs_ms
```

### 3.8 V&V status

- Tests passing: active (part of mission_fsm m5 suite)
- `test_tc_dai_004_alert_near_fast_path_without_hysteresis` — demo suite ✓
- Open gaps: hysteresis on alert downgrade (XFAIL ARCH-DAI), feed timeout edge cases

---

## 4. Subsystem: ACAS Xu

### 4.1 Function

Implements Resolution Advisories (RA) per DO-386 using HorizontalCAS neural networks (.nnet format, Stanford SISL). Operates at shorter time horizons than DAIDALUS — last-resort collision avoidance.

### 4.2 Implementation

- **Node:** `src/acas_node/src/acas_node.cpp` (C++ — not Python)
- **Networks:** `.nnet` files in `src/acas_node/config/nnets/` (pending integration — ARCH-ACAS-NNET)
- **Launch:** `src/acas_node/launch/acas_xu.launch.py`

**Why C++:** The .nnet inference loop requires deterministic, low-latency execution. Python's GIL and garbage collector introduce jitter incompatible with DO-386 timing requirements.

### 4.3 Advisory types

ACAS Xu produces one of 5 advisories per encounter geometry:
- `COC` — Clear of Conflict (no action)
- `DNC` — Do Not Climb
- `DND` — Do Not Descend  
- `DES1500` — Descend at ≥ 1500 fpm
- `CL1500` — Climb at ≥ 1500 fpm

### 4.4 Configuration

```yaml
# acas.yaml
traffic_topic:       "/traffic/intruders"
navigation_topic:    "/navigation/state"
ownship_topic:       "/ownship/state"
use_ownship_fallback: true
nnet_subdir:         "nnets"
rho_norm_m:          185200.0   # 100 nautical miles
v_norm_mps:          250.0      # normalisation speed
timer_period_s:      0.05       # 20 Hz
```

### 4.5 FSM integration

When `acas_abort_from_advisory: true` (VTOL config), an active RA while in CRUISE triggers `abort_command`:

```python
# From mission_fsm_node.py
if use_acas_abort and self._acas_ra_active and self._fsm.state == "CRUISE":
    merged["abort_command"] = True
```

In the default config (`acas_abort_from_advisory: false`), the RA is published but does not directly trigger FSM transitions — the local_replanner acts on it instead.

### 4.6 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/traffic/intruders` | `flightmind_msgs/TrafficReport` | ADS-B |
| `/navigation/state` | `flightmind_msgs/NavigationState` | navigation_bridge |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/acas/advisory` | `flightmind_msgs/ACASAdvisory` | 20 Hz |

```
ACASAdvisory:
  header
  bool ra_active
  int32 threat_class        # 0=NONE 1=HEAD_ON 2=OVERTAKE 3=GENERIC
  float64 climb_rate_mps    # required climb rate
  float64 heading_delta_deg # required heading change
  float64 time_to_cpa_s     # time to closest point of approach
  float64 horizontal_miss_dist_m
```

### 4.7 V&V status

- 2 passed (import + node startup)
- **ARCH-ACAS-NNET open** — .nnet files not integrated. All functional tests are XFAIL.
- HIL blocker.

---

## 5. Subsystem: local_replanner

### 5.1 Function

Tactical evasion layer — computes an immediate heading deviation when DAIDALUS or ACAS indicates an imminent conflict. Operates within the EVENT state: once the FSM transitions to EVENT, the local_replanner takes over route guidance until the conflict is resolved.

Contains **emergency_planner** as internal logic — selects a contingency landing zone when the aircraft cannot safely return to the planned route.

### 5.2 Implementation

- **ROS2 node:** `src/local_replanner/local_replanner/local_replanner_node.py`
- **Core logic:** `src/local_replanner/local_replanner/replan_core.py`
- **Trigger monitor:** `src/local_replanner/local_replanner/trigger_monitor.py`
- **RRT stub:** `src/local_replanner/local_replanner/rrt_local_stub.py` (pending full implementation)

### 5.3 Configuration

```yaml
# local_replanner.yaml
w1: 1.0                          # weight: heading deviation cost
w2: 1.0                          # weight: track deviation cost
w3: 0.5                          # weight: energy cost
qf_threshold: 0.65               # quality_flag below this disables replanning
track_deviation_threshold_m: 80.0 # trigger replan when off-track by this margin
terrain_max_m: 500.0
replan_dt_s: 0.5                 # minimum interval between replans
ref_lat_deg: 40.0                # reference NED origin
ref_lon_deg: -3.0
```

### 4.4 Trigger conditions

The `trigger_monitor` watches for:
- `daidalus_alert_level >= 2` — DAIDALUS MID or NEAR
- `acas_ra_active = True` — ACAS Resolution Advisory active
- Track deviation `> track_deviation_threshold_m` from planned path

### 5.5 Emergency planner (internal)

When `fdir_emergency=True` and `slz_available=True`, the emergency planner selects the nearest reachable safe landing zone from the FDIR emergency zone list, cross-checked against the SLZ detector output. This is the logic that enables the `ABORT→LANDING` FSM transition.

### 5.6 V&V status

- Tests: import passing, phase 6 replan tests passing
- RRT local stub in place — full local RRT not implemented
- Emergency planner: functional in SIL via FSM `slz_available` atom

---

## 6. Subsystem: airspace_monitor

### 6.1 Function

Loads NFZ definitions from UTM/GeoJSON, monitors aircraft containment within authorised airspace, and publishes violation predictions with time-to-violation.

### 6.2 Implementation

- **Monitor node:** `src/upnext_airspace/upnext_airspace/airspace_monitor_node.py`
- **Visualisation:** `src/upnext_airspace/upnext_airspace/airspace_viz_node.py`
- **GeoJSON loader:** `src/upnext_airspace/upnext_airspace/geojson_loader.py`
- **Containment engine:** `src/polycarp_node/polycarp_node/polycarp_core.py` — NASA PolyCARP
- **Launch:** `src/upnext_airspace/launch/airspace_demo.launch.py`

### 6.3 Algorithm: PolyCARP

NASA PolyCARP provides formally verified polygon containment algorithms:
- `contains()` — point in polygon (ray casting)
- `edge_proximity()` — distance to nearest polygon edge
- `time_to_violation()` — given current velocity, when does the aircraft enter the NFZ

**Why PolyCARP over custom implementation:** Formally verified by NASA Langley. Used in production UTM systems. Handles edge cases (concave polygons, boundary crossing) correctly. The alternative — a custom ray casting implementation — would require extensive V&V effort to reach the same confidence level.

### 6.4 NFZ polygon format

NFZ polygons are loaded from GeoJSON published on `/airspace/geofences`. The `parse_geofences_json` function (in `gpp/geometry.py`) converts them to NED coordinate polygon lists for use by both the airspace_monitor and the GPP.

```python
# From gpp/geometry.py — used by both GPP and polycarp_node
def parse_geofences_json(json_str: str) -> List[Polygon]:
    # Expects: {"polygons": [[list of [n,e] vertices], ...]}
    # Each polygon must have >= 3 vertices
```

### 6.5 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/navigation/state` | `flightmind_msgs/NavigationState` | navigation_bridge |
| `/airspace/geofences` | `std_msgs/String` (GeoJSON) | UTM / external |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/polycarp/violation_imminent` | `std_msgs/Bool` | 10 Hz |
| `/polycarp/geofence_status` | `flightmind_msgs/GeofenceStatus` | 10 Hz |

```
GeofenceStatus:
  header
  bool violation_imminent
  float64 time_to_violation_s   # -1 if no violation predicted
  string zone_id
```

### 6.6 V&V status

- `test_polycarp_core.py` passing
- Integrated into mission_fsm m13 safety atoms suite via `geofence_breach` atom
- `test_tc_atom_004_geofence_breach_cruise_to_abort` — demo suite ✓

---

## 7. Design Decisions and Rationale

### 7.1 Why DAIDALUS + ACAS Xu as separate layers

DAIDALUS operates at **strategic** scale (minutes, resolution bands, heading guidance). ACAS Xu operates at **emergency** scale (seconds, binary RA, immediate climb/descend). They address different time horizons and use different algorithms. Merging them would conflate strategic deconfliction with last-resort collision avoidance — a category error.

DO-365 (DAIDALUS) and DO-386 (ACAS Xu) are also separate standards with separate certification requirements. Keeping the implementations separate makes the certification boundary clear.

### 7.2 Why local_replanner in Collision Avoidance and not Trajectory Planning

The local_replanner activates *in response to a detected threat* — it does not plan missions, it evades. Its trigger is always a collision avoidance event (DAIDALUS level ≥ 2, ACAS RA active, track deviation). It belongs with the threat detection system that triggers it, not with the mission planning system.

### 7.3 Why PolyCARP for geofence containment

NASA PolyCARP is formally verified software used in real UTM systems. The alternative — a custom implementation — would require extensive V&V to achieve equivalent confidence. For a DO-178C project, using a vetted external library with known properties is preferable to reimplementing verified algorithms.

---

## 8. Known Limitations and Open Gaps

| Gap | Description | Impact |
|---|---|---|
| ARCH-ACAS-NNET | .nnet neural networks not integrated | No DO-386 compliance — HIL blocker |
| ARCH-DAI | Hysteresis on alert downgrade not implemented | Possible oscillation on MID/NEAR boundary |
| LOCAL-RRT | local_replanner uses stub RRT — no real evasion path | In EVENT state, only heading deviation available |
| NFZ-3D | Geofence only 2D — altitude not enforced | Altitude violations possible |

---

## 9. References

- `src/upnext_icarous_daa/` — DAIDALUS DAA package
- `src/upnext_icarous_bridge/upnext_icarous_bridge/bridge_node.py`
- `src/acas_node/src/acas_node.cpp`
- `src/acas_node/config/acas.yaml`
- `src/local_replanner/local_replanner/local_replanner_node.py`
- `src/local_replanner/config/local_replanner.yaml`
- `src/upnext_airspace/upnext_airspace/airspace_monitor_node.py`
- `src/polycarp_node/polycarp_node/polycarp_core.py`
- `src/flightmind_msgs/msg/DaidalusAlert.msg`
- `src/flightmind_msgs/msg/DaidalusBands.msg`
- `src/flightmind_msgs/msg/ACASAdvisory.msg`
- `src/flightmind_msgs/msg/GeofenceStatus.msg`
