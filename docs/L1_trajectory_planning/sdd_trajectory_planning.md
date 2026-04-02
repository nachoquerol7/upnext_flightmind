 SDD — L2.2 Trajectory Planning

**Document ID:** FM-SDD-L2.2  
**Version:** 1.0  
**Date:** 2026-04-02  
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext Spain  
**Status:** Draft

---

## 1. Purpose

This domain is responsible for determining *what* the aircraft should do at any moment (Mission FSM) and *how* to get there (Global Planner), translating high-level decisions into a sequence of waypoints that the Vehicle Control domain can execute.

---

## 2. Domain Decomposition

```
L2.2 — Trajectory Planning
├── mission_fsm        (pkg: mission_fsm)
├── global_planner     (pkg: gpp)
└── → trajectory_gen   (canonical in L2.5 Vehicle Control)
```

**Why these three together:** The FSM decides the mission state, the Global Planner computes the route for that state, and trajectory_gen converts that route into continuous setpoints. They share a tightly coupled data flow: FSM state changes trigger replanning; planner failures feed back into the FSM as atoms. Separating them would create artificial ICDs between functions that call each other synchronously.

**Rejected alternative — FSM as standalone domain:** The FSM alone has no output useful to the rest of the stack without a planner. Its decisions are meaningless without a route. Coupling is intentional.

---

## 3. Subsystem: mission_fsm

### 3.1 Function

The Mission FSM is the **sole arbiter of mission state**. It consumes boolean atoms from all other domains and applies YAML-defined transitions to determine which of 9 macro-states the aircraft is in. No other node changes mission state.

### 3.2 Implementation

- **Core engine:** `src/mission_fsm/mission_fsm/fsm.py` — `MissionFsm` class
- **ROS2 node:** `src/mission_fsm/mission_fsm/mission_fsm_node.py` — `MissionFsmNode`
- **Configuration:** `src/mission_fsm/config/mission_fsm.yaml` (and platform variants)

### 3.3 States

```
PREFLIGHT   Pre-flight checks. max_duration_sec: 5.0
AUTOTAXI    Ground taxi to runway. max_duration_sec: 5.0
TAKEOFF     Climb to cruise altitude. max_duration_sec: 5.0
CRUISE      Nominal enroute flight. max_duration_sec: 5.0
EVENT       Degraded / conflict mode. max_duration_sec: 5.0
LANDING     Final approach and touchdown.
GO_AROUND   Missed approach recovery.
RTB         Return to base.
ABORT       Terminal safe state. Requires explicit operator reset.
```

### 3.4 Transition logic

Transitions are **first-match ordered** per source state. The engine iterates the YAML transition list top-to-bottom and fires the first matching transition. This gives explicit priority control without complex priority tables.

```python
# From fsm.py — step() core loop
for t in self._transitions:
    if str(t["from"]) != self._state:
        continue
    if not eval_condition(t.get("when", {}), merged, self._context):
        continue
    entry_guard = self._entry.get(str(t["to"]), {})
    if not eval_condition(entry_guard, merged, self._context):
        continue
    self._state = str(t["to"])
    fired = str(t.get("trigger", ""))
    break
```

**Priority from CRUISE** (first-match order):
1. `ABORT` — `abort_command | fdir_emergency | battery_low | geofence_breach`
2. `ABORT` — `battery_critical`
3. `RTB` — `gcs_lost`
4. `RTB` — `c2_lost`
5. `EVENT` — `daidalus_feed_lost`
6. `EVENT` — `daidalus_recovery`
7. `EVENT` — `daidalus_near` (fast-path, no hysteresis)
8. `EVENT` — `quality_degraded | daidalus_escalated`
9. `RTB` — `rtb_command`
10. `LANDING` — `land_command`
11. `ABORT` — `state_dwell_timeout`

### 3.5 Hysteresis

Two analog signals use hysteresis to avoid false transitions:

**quality_flag** (`quality_degraded` atom):
```
quality_degraded = True  when quality_flag < threshold  for >= hysteresis_ticks_on  consecutive ticks
quality_recovered = True when quality_flag > threshold + margin for >= hysteresis_ticks_off ticks
```
Default: `threshold=0.5`, `ticks_on=3`, `ticks_off=5`, `margin=0.05`

**daidalus_alert** (`daidalus_escalated` atom):
```
daidalus_escalated = True when alert_level in [amber..2] for >= daidalus_escalate_ticks ticks
# alert_level 3 (NEAR) bypasses hysteresis — goes direct to EVENT via daidalus_near fast-path
```
Default: `amber=1`, `escalate_ticks=2`

### 3.6 Supervision atoms

The FSM node directly monitors system-level signals with sustain timers:

| Signal | Topic | Timeout | Atom |
|---|---|---|---|
| GCS heartbeat | `/gcs_heartbeat` | `gcs_heartbeat_timeout_sec=2.0` | `gcs_lost` |
| C2 link | `/c2_link_status` | `c2_link_loss_sec=2.0` | `c2_lost` |
| Battery | `/battery_state` | sustain `battery_low_sustain_sec=2.0` | `battery_low` |
| Geofence | `/geofence_breach` + `/polycarp/violation_imminent` | sustain `geofence_breach_sustain_sec=0.5` | `geofence_breach` |
| DAIDALUS feed | `/fsm/in/daidalus_alert` | `daidalus_feed_timeout_sec=2.0` | `daidalus_feed_lost` |

### 3.7 SLZ integration

The FSM subscribes to `/slz/best` (PoseStamped) and `/slz/status` (JSON string). It derives the `slz_available` builtin:

```python
def _builtin_slz_available(i, c):
    age   = float(i.get("slz_best_age_sec", 999.0))
    score = float(i.get("slz_best_score", 0.0))
    return age < 5.0 and score > 0.6
```

Used in the ABORT→LANDING emergency landing transition:
```yaml
- from: ABORT
  to: LANDING
  trigger: abort_slz_emergency_land
  when:
    all: [slz_available, fdir_emergency]
```

### 3.8 Platform variants

| Config file | Platform | Key differences |
|---|---|---|
| `mission_fsm.yaml` | Generic / SIL | Default, all tests |
| `mission_fsm_vtol.yaml` | VTOL | `acas_abort_from_advisory: true` |
| `mission_fsm_heli.yaml` | Helicopter | `go_around_max_attempts: 5` |
| `mission_fsm_male.yaml` | MALE fixed-wing | `c2_timeout_sec: 30`, `bvlos_mode: true` |

### 3.9 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/fsm/in/quality_flag` | `std_msgs/Float64` | navigation_bridge |
| `/fsm/in/daidalus_alert` | `std_msgs/Int32` | DAIDALUS |
| `/fsm/in/fdir_emergency` | `std_msgs/Bool` | fdir |
| `/fsm/in/preflight_ok` | `std_msgs/Bool` | GCS / operator |
| `/fsm/in/takeoff_complete` | `std_msgs/Bool` | trajectory_gen |
| `/fsm/in/land_command` | `std_msgs/Bool` | GCS / operator |
| `/slz/best` | `geometry_msgs/PoseStamped` | landing_zone_detector |
| `/slz/status` | `std_msgs/String` (JSON) | landing_zone_detector |
| `/acas/advisory` | `flightmind_msgs/ACASAdvisory` | acas_node |
| `/gcs_heartbeat` | `std_msgs/Header` | GCS |
| `/c2_link_status` | `std_msgs/Bool` | GCS |
| `/battery_state` | `sensor_msgs/BatteryState` | navigation_bridge |
| `/geofence_breach` | `std_msgs/Bool` | fdir / external |
| `/polycarp/violation_imminent` | `std_msgs/Bool` | polycarp_node |

**Publications:**

| Topic | Type | QoS | Rate |
|---|---|---|---|
| `/fsm/state` | `flightmind_msgs/FSMState` | RELIABLE + TRANSIENT_LOCAL | 20 Hz |
| `/fsm/current_mode` | `std_msgs/String` | default | 20 Hz |
| `/fsm/active_trigger` | `std_msgs/String` | default | 20 Hz |
| `/fsm/heartbeat` | `std_msgs/Bool` | default | 1 Hz |
| `/fmu/in/offboard_control_mode` | `px4_msgs/OffboardControlMode` | default | 10 Hz |

### 3.10 V&V status

- **158 passed**, 23 xfail, 0 failed
- 100% branch coverage on `fsm.py` (113 statements, 60 branches)
- Test suites: m1 (transitions), m2 (timeouts), m3 (integrity), m4 (localisation), m5 (DAIDALUS), m6 (FDIR), m9 (E2E nominal), m10 (E2E faults), m13 (safety atoms)

---

## 4. Subsystem: global_planner

### 4.1 Function

Computes a collision-free, kinematically feasible route from current position to goal, treating NFZ polygons as hard constraints. Also manages flight level assignment and takeoff phase sequencing.

### 4.2 Implementation

- **ROS2 node:** `src/gpp/gpp/gpp_node.py` — `GppNode`
- **Planner core:** `src/gpp/gpp/rrt_star.py` — `RRTStarPlanner`
- **Path geometry:** `src/gpp/gpp/dubins.py` — shortest Dubins path (CSC/CCC)
- **FL assignment:** `src/gpp/gpp/fl_assignment.py` — `compute_assigned_fl`
- **Takeoff:** `src/gpp/gpp/takeoff_manager.py` — `TakeoffManager`

### 4.3 Algorithm: Informed-RRT*

The planner uses **Informed-RRT*** (Gammell 2014) with Dubins edges in SE(2).

**Why Informed-RRT* over alternatives:**

| Algorithm | Rejected reason |
|---|---|
| A* (grid) | Discretisation error, memory cost for large airspace |
| RRT (basic) | Not asymptotically optimal — path quality degrades with NFZ |
| PRM | Pre-computation assumes static NFZ — BVLOS requires dynamic replanning |
| Informed-RRT* | Asymptotically optimal, anytime, ellipsoidal informed sampling converges faster |

**Core parameters:**
```python
RRTStarPlanner(
    turn_radius_m = 600.0,   # from vehicle_model — minimum Dubins radius
    max_iter      = 1200,    # iterations before returning best found
    step_size_m   = 55.0,    # extension step along Dubins edge
    goal_bias     = 0.18,    # probability of sampling goal directly
    seed          = 42,      # deterministic for SIL reproducibility
)
```

**Informed sampling** (active after first solution found):
```python
# Samples within ellipse centred between start and goal
# semi-axes proportional to best_cost * 0.55
cx = (goal[0] + start[0]) / 2.0
rx = min(best_cost * 0.55, (nmax - nmin) / 2.0)
```

**NFZ as hard constraints:**
- Every Dubins edge is collision-checked against all NFZ polygons
- 28 sample points per edge (configurable)
- Uses `point_in_polygon` — ray casting, O(n) per polygon vertex
- NFZ polygon hash cached: replanning only triggered when goal or NFZ changes

```python
def plan_if_needed(self, start, goal, nfz, bounds, goal_tuple, nfz_json):
    gk = self.goal_nfz_key(goal_tuple, nfz_json)
    if gk == self._goal_key:
        return list(self._last_path)  # cache hit — no replan
    # ... replan
```

**Fallback behaviour:**
- If RRT* finds no path and direct Dubins edge is NFZ-free → return `[start, goal]`
- If direct edge hits NFZ → dense Dubins sampling fallback (48 points)
- If no safe path exists → return `[start]` only

### 4.4 Algorithm: Dubins paths

Shortest path between two poses (n, e, heading) with minimum turn radius constraint. Six path types evaluated: LSL, LSR, RSL, RSR, RLR, LRL (L=left turn, R=right turn, S=straight).

```python
_PATHS = [
    ("LSL", -1, 0, -1),
    ("LSR", -1, 0,  1),
    ("RSL",  1, 0, -1),
    ("RSR",  1, 0,  1),
    ("RLR",  1,-1,  1),
    ("LRL", -1, 1, -1),
]
```

CSC paths (Curve-Straight-Curve) and CCC paths (Curve-Curve-Curve) are computed analytically. The shortest feasible path is selected. Interpolation function returns `(n, e, heading)` at any arc length `s`.

**Why Dubins over straight-line segments:** Fixed-wing UAS have a minimum turn radius constraint. Straight-line waypoints create infeasible paths for large platforms (turn_radius_min=600m at 30 m/s). Dubins paths are the shortest kinematically feasible curves.

### 4.5 Flight level assignment

```python
def compute_assigned_fl(terrain_m, ceiling_m, quality_flag, base_margin_m):
    # Returns (fl_amsl_m, status_string)
    # FL = terrain_max + safety_margin + base_margin
    # Degrades margin when quality_flag < threshold
```

Subscribes to `/gpp/terrain_max_m` and `/gpp/ceiling_m` — terrain DEM data from `upnext_bringup/fetch_dem_heightmap.py`.

### 4.6 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/gpp/terrain_max_m` | `std_msgs/Float64` | upnext_bringup (DEM) |
| `/gpp/ceiling_m` | `std_msgs/Float64` | airspace_monitor |
| `/nav/quality_flag` | `std_msgs/Float64` | navigation_bridge |
| `/gpp/goal` | `std_msgs/Float64MultiArray` | mission_fsm / operator |
| `/airspace/geofences` | `std_msgs/String` (GeoJSON) | airspace_monitor |
| `/ownship/state` | `std_msgs/Float64MultiArray` | navigation_bridge |
| `/gpp/takeoff_state` | `std_msgs/Float64MultiArray` | trajectory_gen |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/gpp/global_path` | `nav_msgs/Path` | On replan |
| `/gpp/assigned_fl` | `std_msgs/Float64` | 10 Hz |
| `/gpp/status` | `std_msgs/String` | 10 Hz |
| `/gpp/takeoff_phase` | `std_msgs/String` | 10 Hz |

### 4.7 Configuration

```yaml
# gpp.yaml
base_margin_m:      0.0    # additional safety margin above terrain
turn_radius_min_m:  600.0  # must match vehicle_model
vr_mps:             28.0   # rotation speed for takeoff manager
climb_rate_max_mps: 8.0
pitch_max_deg:      12.0
```

### 4.8 V&V status

- **94 passed**, 2 xfail, 0 failed
- Test suites: m1 (FL assignment), m2 (geometry), m3 (Dubins), m4 (RRT*), m5 (takeoff manager), m6 (node), m7 (integration), m8 (safety regression)
- Demo T1: NFZ avoidance standalone — **PASS, 1.53s**, min_dist=85.1m

---

## 5. Design Decisions and Rationale

### 5.1 Why YAML-driven FSM over code-defined transitions

Allows platform-specific behaviour (VTOL vs helicopter vs MALE) without forking the codebase. The FSM engine (`fsm.py`) is platform-agnostic — only the YAML changes. This is the same pattern used in flight management systems for reconfigurable mission profiles.

Rejected alternative: hardcoded transition tables. Inflexible, requires recompilation for every platform variant, harder to audit for DO-178C.

### 5.2 Why first-match over priority queues

First-match gives **explicit, auditable priority** — the order in the YAML file is the priority order. Anyone reading the YAML can determine exactly which transition fires without executing code. Priority queues require priority values to be consistent across all transitions — a maintenance burden that creates subtle bugs.

### 5.3 Why NFZ as hard constraints, not cost penalties

NFZ violations are a safety requirement, not a performance metric. Any algorithm that treats NFZ as a high cost (but not infinite) might find a path through an NFZ if it improves other metrics sufficiently. Hard constraints guarantee compliance regardless of other objectives.

### 5.4 Why cache path on goal+NFZ hash

Replanning 1200 RRT* iterations on every tick at 10Hz is computationally prohibitive. The hash-based cache ensures replanning only occurs when the mission situation actually changes — new goal or new NFZ configuration.

---

## 6. Known Limitations and Open Gaps

| Gap | Description | Impact |
|---|---|---|
| GPP-013 | NFZ 3D altitude not enforced — only 2D polygon | Altitude violations possible in stratified airspace |
| GPP-033 | Emergency LZ list static (YAML) — no dynamic SLZ integration | Emergency planner not connected to landing_zone_detector |
| ARCH-TRAJ | trajectory_gen not connected to PX4 setpoints | Cannot fly autonomously — HIL blocker |
| FSM dwell | max_duration_sec=5.0 is test value — operational values not defined | Premature timeouts in real flight |

---

## 7. References

- `src/mission_fsm/mission_fsm/fsm.py`
- `src/mission_fsm/mission_fsm/mission_fsm_node.py`
- `src/mission_fsm/config/mission_fsm.yaml`
- `src/mission_fsm/config/mission_fsm_vtol.yaml`
- `src/mission_fsm/config/mission_fsm_heli.yaml`
- `src/mission_fsm/config/mission_fsm_male.yaml`
- `src/gpp/gpp/gpp_node.py`
- `src/gpp/gpp/rrt_star.py`
- `src/gpp/gpp/dubins.py`
- `src/gpp/config/gpp.yaml`
- `src/mission_fsm/docs/vnv/VV_MATRIX.md`
- `src/mission_fsm/docs/vnv/XFAIL_INDEX.md`
