# Trajectory Planning — System Design Description
**FM-SDD-02 · v1.0 · 2026-04-02**
**Status:** active
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext

---

## 1. Purpose

Manages the full mission lifecycle through a 9-state HFSM (DO-178C DAL-C), computes obstacle-free routes with Informed-RRT* + Dubins 3D, and generates continuous trajectory setpoints for PX4 via trajectory_gen at 50 Hz.

---

## 2. BDD [L1 → L2]

```
Trajectory Planning [L1]
  + goal: BVLOS mission management · obstacle-free routing
  + std: DO-178C DAL-C
  │
  ├── L2: mission_fsm      (pkg: mission_fsm)
  │     + 9 states · YAML-driven · first-match transitions
  │     + 158 passed · 23 xfailed · 100% branch coverage
  │
  └── L2: global_planner   (pkg: gpp)
        + Informed-RRT* · Dubins 3D · NFZ hard constraints
        + FL assignment · path caching
        + 94 passed · 2 xfailed

  [trajectory_gen canonical in L1: Vehicle Control]
```

---

## 3. L2 Blocks

| Block | Package | Key outputs | Freq | Status |
|---|---|---|---|---|
| mission_fsm | mission_fsm | /fsm/state · FSMState | 10 Hz RELIABLE+TL | ✓ 158 passed |
| global_planner | gpp | /gpp/path · nav_msgs/Path | on-demand | ✓ 94 passed |

---

## 4. Mission FSM

### 4.1 States and Timeouts

| State | max_duration_sec | Entry guards | Notes |
|---|---|---|---|
| PREFLIGHT | 5.0 | — | Initial state. Operator checks. |
| AUTOTAXI | 5.0 | — | Ground roll to runway/pad |
| TAKEOFF | 5.0 | `taxi_clear` | Climb phase. Critical timeout. |
| CRUISE | 5.0 | — | Nominal enroute. Longest state. |
| EVENT | 5.0 | `quality_degraded OR daidalus_escalated` | Degraded / conflict evaluation |
| LANDING | — | — | No timeout. Controlled descent. |
| GO_AROUND | — | `approach_not_stabilized` | Max attempts: 3 (generic) · 5 (heli) |
| RTB | — | — | No timeout. Return to base. |
| ABORT | — | `fdir_emergency OR abort_command` | Terminal. Operator reset required. |

> ⚠️ All max_duration_sec are test values. Operational values not yet defined.

### 4.2 Transition Graph (all 17 transitions)

| From | To | Trigger | Condition |
|---|---|---|---|
| PREFLIGHT | AUTOTAXI | to_autotaxi | `all: [preflight_ok]` |
| AUTOTAXI | TAKEOFF | to_takeoff | `all: [taxi_clear]` |
| TAKEOFF | CRUISE | to_cruise | `all: [takeoff_complete]` |
| CRUISE | ABORT | cruise_to_abort | `any: [abort_command, fdir_emergency]` |
| CRUISE | EVENT | to_event | `any: [quality_degraded, daidalus_escalated]` |
| CRUISE | RTB | cruise_to_rtb | `all: [rtb_command]` |
| CRUISE | LANDING | to_landing | `all: [land_command]` |
| EVENT | CRUISE | event_to_cruise | `all: [event_cleared]` |
| EVENT | ABORT | event_to_abort | `all: [fdir_emergency]` |
| EVENT | RTB | event_to_rtb | `all: [rtb_during_event]` |
| LANDING | GO_AROUND | landing_to_goaround | `all: [approach_not_stabilized]` |
| LANDING | AUTOTAXI | landing_complete | `all: [touchdown]` |
| GO_AROUND | LANDING | goaround_to_landing | `all: [go_around_complete]` |
| GO_AROUND | CRUISE | goaround_to_cruise | `all: [missed_approach_climb]` |
| ABORT | RTB | abort_to_rtb | `all: []` (immediate) |
| RTB | LANDING | rtb_to_landing | `all: [rtb_landing]` |
| RTB | CRUISE | rtb_to_cruise | `all: [rtb_cancel]` |

**Priority from CRUISE (first-match order):**
1. → ABORT: `abort_command | fdir_emergency` — highest priority, never blocked
2. → EVENT: `quality_degraded | daidalus_escalated`
3. → RTB: `rtb_command`
4. → LANDING: `land_command`

### 4.3 Boolean Atoms

Builtins computed inside MissionFsm.step():

| Atom | Source | Logic |
|---|---|---|
| `quality_degraded` | `/fsm/in/quality_flag` (Float64) | flag < threshold for `hysteresis_ticks_on` consecutive ticks |
| `daidalus_escalated` | `/fsm/in/daidalus_alert` (Int32) | alert >= amber for `daidalus_escalate_ticks` ticks |
| `daidalus_near` | `/fsm/in/daidalus_alert` | alert == 3 — fast-path, no hysteresis |
| `daidalus_recovery` | `/fsm/in/daidalus_alert` | alert >= 4 |
| `fdir_emergency` | `/fsm/in/fdir_emergency` (Bool) | direct passthrough |
| `battery_low` | `/fsm/in/battery_level` (Float64) | level < 0.15 sustained 2.0s |
| `gcs_lost` | heartbeat timeout | no heartbeat for 2.0s |
| `c2_lost` | c2 link timeout | no c2 for 2.0s |
| `geofence_breach` | `/fsm/in/geofence_breach` (Bool) | breach sustained 0.5s |
| `slz_available` | `/slz/best` age + score | age < 5s AND score > 0.6 |

### 4.4 Hysteresis Parameters

| Parameter | Default | Effect |
|---|---|---|
| `quality_flag_threshold` | 0.5 | Below → quality_degraded activates |
| `hysteresis_ticks_on` | 3 | Ticks below threshold before triggering |
| `hysteresis_ticks_off` | 5 | Ticks above threshold+margin before clearing |
| `hysteresis_margin` | 0.05 | Dead band: threshold_off = 0.55 |
| `daidalus_alert_amber` | 1 | First level counting toward escalation |
| `daidalus_escalate_ticks` | 2 | Ticks at amber+ before daidalus_escalated |
| `tick_hz` | 20.0 | FSM evaluation rate (50ms period) |

### 4.5 Platform YAML Variants

| File | Platform | Key difference |
|---|---|---|
| `mission_fsm.yaml` | Generic / SIL | Default |
| `mission_fsm_vtol.yaml` | VTOL | `acas_abort_from_advisory: true` |
| `mission_fsm_heli.yaml` | Helicopter | `go_around_max_attempts: 5` |
| `mission_fsm_male.yaml` | MALE/HALE | `c2_timeout_sec: 30` · `bvlos_mode: true` |

### 4.6 FSMState Message

```
FSMState:
  current_mode: string       # e.g. "CRUISE"
  active_trigger: string     # e.g. "to_event"
  event_substate: string     # XFAIL ARCH-1.3 — not populated
  go_around_count: uint8
```

Published at 10 Hz QoS RELIABLE+TRANSIENT_LOCAL on `/fsm/state`.

### 4.7 Test Coverage

- **158 passed · 23 xfailed · 0 failed**
- 100% branch coverage on `fsm.py` (113 stmts, 60 branches, 0 miss)
- Test modules: M1 transitions · M2 timeouts · M3 integrity · M4 localization interface · M5 DAIDALUS · M6 FDIR · M7 Nav2 · M9 E2E nominal · M10 E2E faults · M11 performance · M13 safety atoms

---

## 5. Global Path Planner (pkg: gpp)

### 5.1 Algorithm: Informed-RRT*

```python
RRTStarPlanner(
    turn_radius_m = 600.0,  # must match vehicle_model.turn_radius_min_m
    max_iter      = 1200,
    step_size_m   = 55.0,
    goal_bias     = 0.18,
    seed          = 42,     # deterministic for SIL
)
```

Once a first solution is found, sampling is biased toward an ellipsoid between start and goal — visible in GppRrtPanel as the shrinking elipse. This is Informed-RRT*: asympotically optimal convergence in continuous space.

### 5.2 Dubins 3D Curves

Waypoints are connected with Dubins curves: shortest path between two configurations (position + heading) with minimum turn radius. Six curve types: LSL, RSR, LSR, RSL, RLR, LRL. Radius violation → segment flagged in DubinsPanel.

### 5.3 Fallback Chain

| Priority | Condition | Output |
|---|---|---|
| 1 | RRT* finds valid path | Full RRT* path |
| 2 | RRT* fails, direct Dubins NFZ-free | `[start, goal]` |
| 3 | RRT* fails, direct chord hits NFZ | Dense Dubins fallback (48 points) |
| 4 | No safe path exists | `[start]` only → Hold |

> Never returns a path that intersects an NFZ. NFZ as hard constraint, not cost.

### 5.4 Path Caching

Replanning only triggered when `SHA256(goal + NFZ_json)[:24]` changes. Avoids 1200-iteration RRT* on every tick.

### 5.5 FL Assignment

```python
compute_assigned_fl(
    terrain_elevation_m,   # if < 0 → returns (nan, 'TERRAIN_INVALID')
    ceiling_m,
    quality_flag,          # lower quality → larger margin
    base_margin_m
)
```

### 5.6 Fixed GPP Bugs

| Gap | Fix |
|---|---|
| GPP-G01: negative terrain silently passed | Guard: base_margin < 0 → TERRAIN_INVALID |
| GPP-G02: NFZ detection with fixed steps=24 | Adaptive sampling: steps = max(24, seg_len / 10m) |
| GPP-G03: RRT* failure returned colliding [start,goal] | Fallback: collision → [start] only |
| GPP-G05: Bounds excluded current UAS position | Bounds include own_n/own_e |
| GPP-G06: Missing terrain/ceiling silently processed | Publishes WAITING and returns |

### 5.7 Test Coverage

- **94 passed · 2 xfailed · 0 failed**
- Key tests: NFZ avoidance (min_dist=85.1m measured), planning time < 2s (1.53s measured), FL assignment with TERRAIN_INVALID, adaptive sampling coverage

---

## 6. Open Gaps

| ID | Description | HIL blocker |
|---|---|---|
| ARCH-1.3 | EVENT substate not exposed in /fsm/current_mode | No |
| ARCH-1.9 | Interrupt waypoint not persisted for resumption | No |
| ARCH-VM | vehicle_model not wired to GPP is_feasible | No |
| ARCH-UTM | Dynamic UTM restriction interface missing | No |
| ARCH-DAI-RECOVERY | DAIDALUS RECOVERY level (4) not mapped in FSM | No |
| ARCH-DAI-FEED | DAIDALUS feed timeout not implemented | No |
