# CONTEXT.md — Flightmind Autonomy Stack

> **Single source of truth for LLMs and humans picking up this project.**
> Update this file in every commit that changes architecture, closes a gap, or adds a document.
> Rule: never let this file be more than one sprint out of date.

---

## Project Identity

| Field | Value |
|---|---|
| Project | Flightmind Autonomy Stack |
| Organisation | UpNext / Airbus UpNext Spain, Getafe |
| Workspace | `~/upnext_uas_ws` |
| ROS distro | ROS2 Jazzy (Ubuntu 24.04 LTS) |
| Flight controller | PX4 Autopilot (uXRCE-DDS bridge) |
| Compute target | Jetson Orin 16GB (inference) + Intel NUC 12 (stack) |
| Next milestone | **Demo — 8 April 2026** (Rodney Rodrigues Robles + Miguel Ángel Vilaplana) |

---

## Environment Setup

```bash
# Source order — always in this sequence
source /opt/ros/jazzy/setup.bash
source ~/archive_repos/ros2_ws/src/install/setup.bash
source ~/upnext_uas_ws/install/setup.bash
```

**Run demo suite:**
```bash
cd ~/upnext_uas_ws/src/mission_fsm
python3 -m pytest -c pytest_demo.ini -m demo -v --timeout=30
```

**Run T1 GPP NFZ test:**
```bash
cd ~/upnext_uas_ws/src/gpp
python3 -m pytest test/demo/test_demo_t1_gpp_nfz.py -v
```

**Launch demo (single command):**
```bash
~/upnext_uas_ws/demo.sh
```

**HTML simulator (9 states):**
```bash
python3 ~/upnext_uas_ws/simulator/launch_simulator.py
# or double-click Simulator.desktop
```

---

## Demo Status — 8 April 2026

| Element | Status |
|---|---|
| Demo suite FSM (6 tests) | ✅ 6 passed, 6.16s |
| T1 GPP NFZ standalone | ✅ PASS, 1.53s, min_dist=85.1m |
| demo.sh single launcher | ✅ working |
| XFAIL_INDEX.md | ✅ ARCH-1.7 split FSM/WATCHDOG |
| VV_MATRIX.md | ✅ copied to mission_fsm/docs/vnv/ |
| HTML simulator 9 states | ✅ updated (AUTOTAXI, GO_AROUND, ABORT reachable) |
| Simulator.desktop | ✅ double-click, pywebview |

---

## Architecture

### System hierarchy

```
L0 — UAS (complete aircraft — context only)
L1 — Flightmind Autonomy Stack
  L2.1 — Perception & Navigation
  L2.2 — Trajectory Planning
  L2.3 — Collision Avoidance
  L2.4 — Health Management
  L2.5 — Vehicle Control
```

### L2 decomposition — closed, do not change without updating this file

```
L2.1 — PERCEPTION & NAVIGATION
  slam_engine              pkg: perception_bridge        (FAST-LIVO2 target, stub)
  navigation_bridge        pkg: navigation_bridge        (EKF2, quality_flag, 50Hz)
  landing_zone_detector    pkg: slz_detector             (U-Net + point cloud, stub)

L2.2 — TRAJECTORY PLANNING
  mission_fsm              pkg: mission_fsm              (HFSM, 9 states, DO-178C DAL-C)
  global_planner           pkg: gpp                      (Informed-RRT* + Dubins, NFZ hard)
  → trajectory_gen         canonical in L2.5

L2.3 — COLLISION AVOIDANCE
  DAIDALUS                 pkg: upnext_icarous_daa       (NASA v2, DO-365)
  ACAS Xu                  pkg: acas_node (C++)          (HorizontalCAS .nnet, DO-386)
  local_replanner          pkg: local_replanner          (tactical evasion)
    emergency_planner      internal to local_replanner
  airspace_monitor         pkg: upnext_airspace + polycarp_node  (PolyCARP, NFZ)

L2.4 — HEALTH MANAGEMENT
  fdir                     pkg: fdir                     (4 detectors, 20Hz, <500ms P99)
    watchdog               internal to fdir              (XFAIL ARCH-1.7-WATCHDOG)
  c2_monitor               pkg: fdir/c2_monitor_node.py
  battery_monitor          pkg: fdir/battery_monitor_node.py

L2.5 — VEHICLE CONTROL
  vehicle_model            pkg: vehicle_model            (envelope, platform_adapter internal)
  trajectory_gen           pkg: trajectory_gen           (Dubins 3D, 50Hz setpoints)
  PX4 interface            uXRCE-DDS
```

### Package name → architecture name mapping

| Package (code) | Architecture name | Domain |
|---|---|---|
| `perception_bridge` | slam_engine | L2.1 |
| `navigation_bridge` | navigation_bridge | L2.1 |
| `slz_detector` | landing_zone_detector | L2.1 |
| `mission_fsm` | mission_fsm | L2.2 |
| `gpp` | global_planner | L2.2 |
| `trajectory_gen` | trajectory_gen | L2.5 |
| `upnext_icarous_daa` | DAIDALUS | L2.3 |
| `acas_node` | ACAS Xu | L2.3 |
| `local_replanner` | local_replanner | L2.3 |
| `upnext_airspace` + `polycarp_node` | airspace_monitor | L2.3 |
| `fdir` | fdir + c2_monitor + battery_monitor | L2.4 |
| `vehicle_model` | vehicle_model | L2.5 |

> **Note:** Package names do not match architecture names — intentional, rename planned post-demo.
> In documents: use architecture name with `(pkg: xxx)` in parentheses.

---

## Closed Architecture Decisions

These are final. Do not reopen without a documented ADR.

| Decision | Rationale |
|---|---|
| trajectory_gen canonical in L2.5 | Its consumer is PX4, not the planner. Execution ≠ planning. |
| platform_adapter internal to vehicle_model | Pure parameter set, not a node. YAML config only. |
| emergency_planner internal to local_replanner | Activates only in response to CA events. Not a standalone planner. |
| airspace_monitor in L2.3, not L2.1 | Output is a threat signal (ABORT atom), not a navigation estimate. |
| watchdog internal to fdir | Same package, shared config, no separate ROS2 node warranted. |
| FSM first-match transitions | Explicit auditable priority. YAML order = priority order. DO-178C friendly. |
| NFZ as hard constraints in RRT* | Safety requirement, not cost. Penalties can always be traded off. |
| quality_flag as scalar | Single consistent signal across all consumers. Full covariance in NavigationState if needed. |
| BEST_EFFORT QoS for VehicleOdometry | Stale odometry worse than no odometry. Freshness > reliability at 50Hz. |
| Static LZ + dynamic SLZ | Static zones = guaranteed fallback. SLZ = enhancement, not dependency. |
| YAML-driven FSM | Platform variants without code forks. DO-178C: config changes, not code changes. |

---

## Open Architecture Gaps

| ID | Description | HIL blocker | Status |
|---|---|---|---|
| ARCH-1.7-WATCHDOG | watchdog_node not implemented | Yes | Open |
| ARCH-ACAS-NNET | ACAS Xu .nnet neural networks not integrated | Yes | Open |
| ARCH-TRAJ | trajectory_gen not connected to PX4 setpoints | Yes | Open |
| ARCH-PERC | FAST-LIVO2 SLAM not integrated | Yes | Open |
| ARCH-SLZ | SLZ U-Net model not trained | No | Open |
| ARCH-FDIR-SEV | Severity table not versioned, combined faults not modelled | No | Open |
| ARCH-VM | vehicle_model not wired to GPP is_feasible | No | Open |

**HIL entry criteria:** 0 failures · ≤15 XFAIL · ARCH-ACAS-NNET closed · ARCH-TRAJ closed · ARCH-PERC validated.

---

## Mission FSM Detail

### States and dwell timeouts

| State | max_duration_sec | Notes |
|---|---|---|
| PREFLIGHT | 5.0 (test value) | Operator checks |
| AUTOTAXI | 5.0 (test value) | Ground roll to runway |
| TAKEOFF | 5.0 (test value) | Climb phase |
| CRUISE | 5.0 (test value) | Nominal enroute |
| EVENT | 5.0 (test value) | Degraded / conflict |
| LANDING | — | No timeout |
| GO_AROUND | — | No timeout |
| RTB | — | No timeout |
| ABORT | — | Terminal. Operator reset required. |

> ⚠️ All max_duration_sec values are test values only. Operational values not yet defined.

### Transition priorities from CRUISE (first-match order)

1. → ABORT: `abort_command | fdir_emergency | battery_low | geofence_breach`
2. → ABORT: `battery_critical`
3. → RTB: `gcs_lost`
4. → RTB: `c2_lost`
5. → EVENT: `daidalus_feed_lost`
6. → EVENT: `daidalus_recovery`
7. → EVENT: `daidalus_near` (fast-path, no hysteresis)
8. → EVENT: `quality_degraded | daidalus_escalated`
9. → RTB: `rtb_command`
10. → LANDING: `land_command`
11. → ABORT: `state_dwell_timeout`

### ABORT→LANDING exception
```yaml
- from: ABORT
  to: LANDING
  trigger: abort_slz_emergency_land
  when:
    all: [slz_available, fdir_emergency]
# slz_available: /slz/best age < 5s AND score > 0.6
```

### Hysteresis parameters (default config)

| Parameter | Default | Effect |
|---|---|---|
| `quality_flag_threshold` | 0.5 | Below this → quality_degraded |
| `hysteresis_ticks_on` | 3 | Ticks below threshold before triggering |
| `hysteresis_ticks_off` | 5 | Ticks above threshold+margin before clearing |
| `hysteresis_margin` | 0.05 | Dead band above threshold |
| `daidalus_alert_amber` | 1 | First alert level that counts toward escalation |
| `daidalus_escalate_ticks` | 2 | Ticks at amber/mid before daidalus_escalated |
| `tick_hz` | 20.0 | FSM evaluation rate |

### Platform YAML configs

| File | Platform | Key difference |
|---|---|---|
| `mission_fsm.yaml` | Generic / SIL | Default |
| `mission_fsm_vtol.yaml` | VTOL | `acas_abort_from_advisory: true` |
| `mission_fsm_heli.yaml` | Helicopter | `go_around_max_attempts: 5` |
| `mission_fsm_male.yaml` | MALE | `c2_timeout_sec: 30`, `bvlos_mode: true` |

---

## FDIR Detail

### Fault detectors

| Detector | Trigger | Fault name |
|---|---|---|
| Navigation quality | `quality_flag < nav_mild_below (0.65)` | NAV_MILD |
| Navigation quality | `quality_flag < nav_severe_below (0.35)` | NAV_SEVERE |
| Navigation quality | `quality_flag < nav_critical_below (0.15)` | NAV_CRITICAL |
| Motor loss | High throttle + negative vert accel sustained `motor_loss_window_s (2.0s)` | MOTOR_DEGRADED |
| Sensor timeout | No quality_flag for `sensor_timeout_nav_quality_s (3.0s)` | NAV_CRITICAL |
| C2 loss | No heartbeat for `c2_heartbeat_timeout_s (1.5s)` | C2_LOST |

### Severity table (fdir_severity.yaml)

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

### C2 loss contingency sequence (EU 2019/947 Annex III)

```
C2 lost (c2_heartbeat_timeout_s = 1.5s)
  → hold  30s  (link_loss_hold_s)
  → RTB   30s  (link_loss_rtb_s)
  → land 120s  (link_loss_land_s)
```

### Emergency landing zones (fdir.yaml)

```yaml
- lat: 40.05  lon: -3.02  runway_m: 900   quality: 0.95
- lat: 40.50  lon: -3.50  runway_m: 1200  quality: 0.85
- lat: 41.20  lon: -2.00  runway_m: 800   quality: 0.70
# Reachability = glide_ratio (18) × altitude_AMSL_m
```

---

## GPP / RRT* Detail

### Parameters

```python
RRTStarPlanner(
    turn_radius_m = 600.0,  # must match vehicle_model.turn_radius_min_m
    max_iter      = 1200,
    step_size_m   = 55.0,
    goal_bias     = 0.18,
    seed          = 42,     # deterministic for SIL
)
```

### Path caching

Replanning only triggered when `SHA256(goal + NFZ_json)[:24]` changes.
No replan on every tick — avoids 1200-iteration RRT* at 10Hz.

### Fallback chain

1. RRT* finds path → return full path
2. RRT* fails, direct Dubins NFZ-free → return `[start, goal]`
3. RRT* fails, direct chord hits NFZ → dense Dubins fallback (48 points)
4. No safe path → return `[start]` only

---

## Vehicle Envelope (default fixed-wing proxy)

```
v_min_ms:              30.0 m/s
v_max_ms:              57.0 m/s
turn_radius_min_m:     600.0 m
climb_rate_max_mps:    8.0 m/s
descent_rate_max_mps:  5.0 m/s
glide_ratio:           18.0
MTOW_kg:               750.0
fuel_mass_initial_kg:  120.0
fuel_burn_kgh:         50.0
v_min_reserve_gain_ms: 5.0   # v_min increase as fuel depletes
```

---

## DAIDALUS Alert Levels → FSM Response

| Level | Name | FSM response |
|---|---|---|
| 0 | NONE | — |
| 1 | FAR | Hysteresis count starts |
| 2 | MID | `daidalus_escalated` → EVENT (after escalate_ticks) |
| 3 | NEAR | `daidalus_near` → EVENT immediately (no hysteresis) |
| 4 | RECOVERY | `daidalus_recovery` → allows return toward CRUISE |

---

## Message Types (flightmind_msgs)

| Message | Key fields |
|---|---|
| `NavigationState` | position_ned[3], velocity_ned[3], orientation_quat[4], covariance_6x6[36], quality_flag, gnss_available, fuel_consumed_kg |
| `FSMState` | current_mode, active_trigger, event_substate, go_around_count |
| `DaidalusAlert` | alert_level (0-4), time_to_violation_s, min_horizontal_dist_m, num_conflict_traffic |
| `DaidalusBands` | heading_bands_deg[], gs_bands_ms[], vs_bands_ms[], recommended_heading_deg |
| `ACASAdvisory` | ra_active, threat_class (0-3), climb_rate_mps, heading_delta_deg, time_to_cpa_s |
| `GeofenceStatus` | violation_imminent, time_to_violation_s, zone_id |
| `TrafficIntruder` | intruder_id, position_ned[3], velocity_ned[3], cooperative, timestamp_s |
| `TrajectorySetpoint` | position_ned[3], velocity_ned[3] |
| `VehicleModelState` | current_weight_kg, v_min_ms, v_max_ms, turn_radius_min_m, glide_ratio, elapsed_mission_h |

---

## V&V Status

| Package | Passed | XFail | Failed |
|---|---|---|---|
| mission_fsm | 158 | 23 | 0 |
| gpp | 94 | 2 | 0 |
| fdir | 22 | 0 | 0 |
| acas_node | 2 | 0 | 0 |
| navigation_bridge | 4 | 0 | 1 |
| slz_detector | 10 | 0 | 0 |
| trajectory_gen | 3 | 0 | 0 |
| vehicle_model | 2 | 0 | 0 |
| **Total** | **295** | **25** | **1** |

---

## Documentation Tree

All docs live in `~/upnext_uas_ws/docs/`. Source of truth is Markdown. PDFs are generated artifacts.

```
docs/
├── L0_flightmind/
│   └── sdd_flightmind.md              ✅ complete
├── L1_perception_navigation/
│   ├── sdd_perception_navigation.md   ✅ complete
│   ├── L2_slam_engine/
│   ├── L2_navigation_bridge/
│   └── L2_landing_zone_detector/
├── L1_trajectory_planning/
│   ├── sdd_trajectory_planning.md     ✅ complete
│   ├── L2_mission_fsm/
│   └── L2_global_planner/
├── L1_collision_avoidance/
│   ├── sdd_collision_avoidance.md     ✅ complete
│   ├── L2_daidalus/
│   ├── L2_acas_xu/
│   ├── L2_local_replanner/
│   └── L2_airspace_monitor/
├── L1_health_management/
│   ├── sdd_health_management.md       ✅ complete
│   ├── L2_fdir/
│   ├── L2_c2_monitor/
│   └── L2_battery_monitor/
└── L1_vehicle_control/
    ├── sdd_vehicle_control.md         ✅ complete
    ├── L2_vehicle_model/
    └── L2_trajectory_gen/
```

### Documents pending (post-demo)

| Document | Where | Priority |
|---|---|---|
| `requirements_*.md` | Each L1 and L2 | High |
| `icd_*.md` | Each L1 | High |
| `vnv_plan_*.md` | Each L1 | High |
| `sdd_*.md` per L2 | Each L2 folder | Medium |
| `conops.md` | L0 | High (SORA) |
| `fha.md` | L0 | High (ARP4754A) |
| `decisions.md` (ADR log) | L0 | Medium |
| `glossary.md` | L0 | Medium |

---

## Key File Paths

```
~/upnext_uas_ws/                                    main workspace
~/upnext_uas_ws/docs/                               documentation root (in git)
~/upnext_uas_ws/docs/_repo_doc_bundle.txt           full repo dump (108KB, ~2819 lines)
~/upnext_uas_ws/demo.sh                             demo launcher
~/upnext_uas_ws/src/mission_fsm/pytest_demo.ini     6-test demo suite config
~/upnext_uas_ws/src/mission_fsm/config/mission_fsm.yaml
~/upnext_uas_ws/src/mission_fsm/docs/vnv/XFAIL_INDEX.md
~/upnext_uas_ws/src/mission_fsm/docs/vnv/VV_MATRIX.md
~/upnext_uas_ws/src/gpp/test/demo/test_demo_t1_gpp_nfz.py
~/upnext_uas_ws/src/fdir/config/fdir.yaml
~/upnext_uas_ws/src/fdir/config/fdir_severity.yaml
~/upnext_uas_ws/src/vehicle_model/config/vehicle_model.yaml
~/upnext_uas_ws/simulator/index.html                HTML5 simulator (9 states)
~/upnext_uas_ws/simulator/launch_simulator.py
~/upnext_uas_ws/simulator/Simulator.desktop
~/archive_repos/ros2_ws/src/install/setup.bash      underlay (px4_msgs etc.)
```

---

## Applicable Standards

| Standard | Domain |
|---|---|
| DO-178C DAL-C | Mission FSM — 100% branch coverage |
| DO-365 | DAIDALUS DAA |
| DO-386 | ACAS Xu |
| ARP4754A §6 | FDIR functional hazard assessment |
| EU 2019/947 Annex III | C2 loss contingency, BVLOS |
| SORA | Specific Operations Risk Assessment |
| ROS2 REP 103 | Coordinate frames (NED) |
| STANAG 4671 | UAS airworthiness baseline |

---

## Git Conventions

```bash
# Always commit docs separately — never git add -A from workspace root
git add docs/path/to/file.md
git commit -m "docs: description"

# Commit prefixes
docs:   documentation changes
feat:   new functionality
fix:    bug fix
test:   test additions or fixes
refactor: code restructure, no behaviour change
arch:   architecture decision — must update CONTEXT.md
# When updating CONTEXT.md, note it in the commit message
git commit -m "arch: move trajectory_gen to L2.5 — update CONTEXT.md"
```

---

## How to Use This File

**Starting a new Claude session:**
Paste the content of this file at the start of the conversation. Claude will have full architectural context without needing to re-read the codebase.

**Starting a new Cursor session:**
This file is in the repo root. Reference it with `@CONTEXT.md` in any Cursor prompt for instant context.

**When something changes:**
Update the relevant section immediately. A stale CONTEXT.md is worse than no CONTEXT.md.
