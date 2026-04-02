# SDD-00 — Flightmind Autonomy Stack

**Document ID:** FM-SDD-00  
**Version:** 1.0  
**Date:** 2026-04-02  
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext Spain  
**Status:** Draft

---

## 1. Purpose and Scope

This document describes the software architecture of the **Flightmind Autonomy Stack** — the onboard intelligence layer that enables safe, autonomous BVLOS (Beyond Visual Line of Sight) operations for Uncrewed Aerial Systems (UAS) across multiple platform types.

Flightmind is **L1** within the overall UAS system hierarchy. L0 is the complete UAS — airframe, propulsion, onboard hardware, and ground segment. This SDD describes L1 and its decomposition into five functional domains (L2).

---

## 2. System Context (L0)

### 2.1 L0 boundary

The UAS system (L0) comprises:

| Element | Description |
|---|---|
| Airframe | Platform-agnostic: fixed-wing, VTOL, helicopter, MALE |
| PX4 Autopilot | Flight controller — runs EKF2, actuator mixing, low-level control |
| Onboard compute | Jetson Orin (inference) + Intel NUC (stack) |
| Sensors | LiDAR, stereo camera, IMU, GNSS, barometer, magnetometer, ESC telemetry |
| Ground Control Station | Operator interface — sends mission authorisation and receives telemetry |
| UTM / U-space | Airspace management — provides NFZ GeoJSON, NOTAM |
| Air traffic | ADS-B receivers — cooperative and non-cooperative intruders |

### 2.2 External actors and interfaces

```
┌──────────────────────────────────────────────────────────┐
│                      UAS (L0)                            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Flightmind Stack (L1)                  │   │
│  │                                                  │   │
│  │  Perception │ Navigation │ Trajectory Planning   │   │
│  │  Collision Avoidance │ Health Mgmt │ Vehicle Ctrl│   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│               PX4 (uXRCE-DDS bridge)                    │
│                         │                                │
│         Sensors ────────┘──────── Actuators             │
└──────────────────────────────────────────────────────────┘
         │                    │                   │
       GCS               UTM / U-space        ADS-B / Radar
   MAVLink 2.0            NFZ GeoJSON         TrafficIntruder
```

**Inputs from external actors:**

| Actor | Interface | Data |
|---|---|---|
| PX4 | uXRCE-DDS `/fmu/out/vehicle_odometry` | Position, velocity, attitude, covariance |
| PX4 | uXRCE-DDS `/fmu/out/vehicle_imu` | IMU delta velocity |
| PX4 | uXRCE-DDS `/fmu/out/vehicle_status` | Arming state, failure detector |
| GCS | `/gcs_heartbeat`, `/c2_link_status` | Operator presence, C2 link status |
| GCS | `/battery_state` | Battery percentage |
| UTM | `/airspace/geofences` | NFZ polygons as GeoJSON |
| ADS-B | `/traffic/intruders` | TrafficIntruder array |

**Outputs to external actors:**

| Actor | Interface | Data |
|---|---|---|
| PX4 | uXRCE-DDS `/fmu/in/offboard_control_mode` | Offboard heartbeat |
| PX4 | `/trajectory/setpoint` | TrajectorySetpoint (position + velocity NED) |
| GCS | `/fsm/state` | FSMState (mode, trigger, event_substate) |
| GCS | `/fdir/active_fault`, `/fdir/policy_action` | Fault status and response |
| GCS | `/navigation/heartbeat` | Navigation system health |

---

## 3. Architecture Overview

### 3.1 Design principles

**Fail-safe by default.** The Mission FSM can only exit ABORT via explicit operator reset. FDIR publishes `fdir_emergency` synchronously within 500ms P99. Battery critical and geofence breach trigger ABORT from CRUISE without passing through EVENT.

**Configuration over code.** No safety parameter is hardcoded. FSM states, transitions, entry guards, dwell timeouts, hysteresis thresholds, and severity tables are all in versioned YAML. Platform-specific configs exist for fixed-wing (`mission_fsm.yaml`), VTOL (`mission_fsm_vtol.yaml`), helicopter (`mission_fsm_heli.yaml`), and MALE (`mission_fsm_male.yaml`).

**Platform agnosticism.** The stack is independent of airframe type. The vehicle_model block encapsulates platform-specific envelope parameters (v_min, v_max, turn_radius_min, glide_ratio). PX4 is the hardware abstraction layer — the stack never issues direct actuator commands.

**Traceability.** Every requirement has an ID, a test case, and an implementation trace. The V&V matrix closes the SR→TC loop. XFAIL entries reference named architecture gaps (ARCH-X.X) with explicit open/closed status.

### 3.2 Technology stack

| Layer | Technology | Rationale |
|---|---|---|
| Middleware | ROS2 Jazzy (Ubuntu 24.04 LTS) | Real-time capable, uXRCE-DDS native, colcon CI |
| Flight control | PX4 Autopilot + MAVLink 2.0 | Industry standard UAS, BSD licence, multi-platform |
| Navigation | EKF2 (PX4) + FAST-LIVO2 (target) | EKF2 for GNSS nominal; FAST-LIVO2 for GNSS-denied |
| DAA | NASA DAIDALUS v2 + HorizontalCAS .nnet | DO-365 / DO-386 compliant, validated in UTM |
| Geofence | NASA PolyCARP | Formally verified polygon containment |
| Path planning | Informed-RRT* + Dubins curves | Asymptotically optimal, NFZ as hard constraints |
| SLZ detection | U-Net + YOLOv8 (target) | State of art 2024-25 for aerial terrain classification |
| Message types | flightmind_msgs (custom) | NavigationState, FSMState, DaidalusAlert, ACASAdvisory, ... |
| SIL testbench | rosbridge WebSocket + pytest + colcon | DO-178C DAL-C compatible, 100% branch coverage on FSM |
| Hardware target | Jetson Orin 16GB + Intel NUC 12 | GPU for neural inference, low-latency compute |

### 3.3 Applicable standards

| Standard | Applies to |
|---|---|
| DO-178C DAL-C | Mission FSM software — 100% branch coverage required |
| DO-365 | DAIDALUS DAA — alert levels, bands, Well-Clear definition |
| DO-386 | ACAS Xu — resolution advisories, threat classification |
| ARP4754A §6 | FDIR functional hazard assessment methodology |
| EU 2019/947 Annex III | C2 loss contingency procedures, BVLOS operations |
| STANAG 4671 | UAS airworthiness baseline |
| SORA | Specific Operations Risk Assessment for operational approval |
| ROS2 REP 103 | Coordinate frames (NED), message conventions |

---

## 4. L2 Functional Domain Decomposition

Flightmind decomposes into five functional domains. Each domain owns a set of ROS2 nodes with a cohesive responsibility and a well-defined external interface.

```
Flightmind Autonomy Stack (L1)
│
├── L2.1  PERCEPTION & NAVIGATION
│         What am I perceiving? Where am I?
│
├── L2.2  TRAJECTORY PLANNING
│         What should I do and how do I get there?
│
├── L2.3  COLLISION AVOIDANCE
│         Is something threatening me right now?
│
├── L2.4  HEALTH MANAGEMENT
│         Is the system functioning correctly?
│
└── L2.5  VEHICLE CONTROL
          Execute the planned trajectory on the aircraft.
```

### 4.1 L2.1 — Perception & Navigation

**Responsibility:** Produce the aircraft's own state (position, velocity, attitude, quality) and understand the immediate physical environment (terrain, safe landing zones, airspace constraints).

**Key nodes:**

| Node | Package | Function |
|---|---|---|
| `navigation_bridge_node` | `navigation_bridge` | Adapts PX4 `VehicleOdometry` → `NavigationState` + `quality_flag` at 50 Hz |
| `slam_node` | `perception_bridge` | FAST-LIVO2 stub — LiDAR+Camera+IMU → `/slam/pose`, `/slam/map`, `/slam/quality` |
| `slz_node` | `slz_detector` | Safe Landing Zone detection — U-Net + point cloud → `/slz/candidates`, `/slz/best` |
| `polycarp_node` | `polycarp_node` | PolyCARP geofence monitoring → `/polycarp/violation_imminent`, `GeofenceStatus` |
| `airspace_monitor_node` | `upnext_airspace` | Loads NFZ GeoJSON, publishes `/airspace/geofences`, visualises boundaries |

**Primary output:** `NavigationState` on `/navigation/state` at 50 Hz QoS RELIABLE+TRANSIENT_LOCAL.

```
NavigationState:
  position_ned[3]    # North, East, Down (m)
  velocity_ned[3]    # Vn, Ve, Vd (m/s)
  orientation_quat[4]# w, x, y, z
  covariance_6x6[36] # flattened pose covariance
  quality_flag       # 0.0 (failed) .. 1.0 (nominal)
  gnss_available     # derived: quality_flag > 0.5
  fuel_consumed_kg   # accumulated since takeoff
```

**Quality flag logic** (from `navigation_bridge_node.py`):

```python
def _quality_from_cov(self, c0: float) -> float:
    # c0 = pose_covariance[0] from PX4 EKF2 upper-triangle
    if c0 > 5.0:  return 0.3   # strong degradation
    if c0 > 1.0:  return 0.7   # moderate degradation
    return 1.0                  # nominal
# quality_flag = 0.0 if no odometry received for > 1.0s
```

The FSM consumes `quality_flag` via `/fsm/in/quality_flag` with hysteresis (`hysteresis_ticks_on=3`, `hysteresis_ticks_off=5`, `hysteresis_margin=0.05`) to avoid false EVENT triggers.

### 4.2 L2.2 — Trajectory Planning

**Responsibility:** Determine the mission state and compute an executable route. The Mission FSM arbitrates *what* to do; the Global Planner computes *how* to get there; the Trajectory Generator converts waypoints into continuous setpoints for PX4.

**Key nodes:**

| Node | Package | Function |
|---|---|---|
| `mission_fsm_node` | `mission_fsm` | HFSM — 9 states, YAML transitions, first-match ordering |
| `gpp_node` | `gpp` | Informed-RRT* + Dubins — NFZ as hard constraints, FL assignment |
| `trajectory_gen_node` | `trajectory_gen` | Dubins 3D waypoint follower → `TrajectorySetpoint` at 50 Hz |
| `vehicle_model_node` | `vehicle_model` | Platform envelope — `is_feasible`, `VehicleModelState` |

**FSM states and platform variants:**

The FSM is fully defined in YAML. Three platform configs exist:

```
mission_fsm.yaml         ← default (generic / SIL tests)
mission_fsm_vtol.yaml    ← VTOL: acas_abort_from_advisory=true
mission_fsm_heli.yaml    ← helicopter: go_around_max_attempts=5
mission_fsm_male.yaml    ← MALE: c2_timeout_sec=30, bvlos_mode=true
```

**State machine — 9 states:**

```
PREFLIGHT → AUTOTAXI → TAKEOFF → CRUISE ─────────────────┐
                                   │                      │
                              EVENT ←────── quality_degraded
                                   │        daidalus_escalated
                                   │        daidalus_near (fast-path)
                              LANDING → GO_AROUND
                                   │
                                  RTB → LANDING
                                   │
                                ABORT  (terminal — operator reset required)
```

**Key transition priorities from CRUISE** (first-match, in order):
1. `ABORT` — `abort_command | fdir_emergency | battery_low | geofence_breach`
2. `ABORT` — `battery_critical`
3. `RTB` — `gcs_lost` or `c2_lost`
4. `EVENT` — `daidalus_feed_lost` | `daidalus_near` (fast-path) | `quality_degraded` | `daidalus_escalated`
5. `RTB` — `rtb_command`
6. `LANDING` — `land_command`

**ABORT→LANDING exception** (SLZ integration):
```yaml
- from: ABORT
  to: LANDING
  trigger: abort_slz_emergency_land
  when:
    all: [slz_available, fdir_emergency]
# slz_available: /slz/best received < 5s ago AND score > 0.6
```

**Vehicle model parameters** (fixed-wing proxy, all platforms):
```
v_min_ms:           30.0 m/s  (raised as fuel depletes)
v_max_ms:           57.0 m/s
turn_radius_min_m:  600.0 m
climb_rate_max_mps: 8.0 m/s
descent_rate_max_mps: 5.0 m/s
glide_ratio:        18.0
MTOW_kg:            750.0
fuel_burn_kgh:      50.0
```

### 4.3 L2.3 — Collision Avoidance

**Responsibility:** Detect and resolve traffic conflicts and airspace violations. Operates independently of trajectory planning — reactive to external threats.

**Key nodes:**

| Node | Package | Function |
|---|---|---|
| `upnext_icarous_daa` | `upnext_icarous_daa` | DAIDALUS v2 — 4 alert levels, heading/GS/VS bands |
| `acas_node` (C++) | `acas_node` | HorizontalCAS .nnet — Resolution Advisories, DO-386 |
| `local_replanner_node` | `local_replanner` | Tactical evasion triggered by DAIDALUS/ACAS |
| `upnext_icarous_bridge` | `upnext_icarous_bridge` | ICAROUS ↔ ROS2 bridge |

**DAIDALUS alert levels and FSM response:**

| Level | Name | Meaning | FSM response |
|---|---|---|---|
| 0 | NONE | No conflict | — |
| 1 | FAR | Preventive alert | Hysteresis count starts |
| 2 | MID | Corrective alert | `daidalus_escalated` → EVENT |
| 3 | NEAR | Warning alert | `daidalus_near` fast-path → EVENT immediately |
| 4 | RECOVERY | Post-conflict recovery | `daidalus_recovery` → back to EVENT/CRUISE |

**ACAS Xu** (C++ node, `src/acas_node/src/acas_node.cpp`):
- Subscribes to `/traffic/intruders` (`TrafficReport`) and `/navigation/state`
- Uses HorizontalCAS .nnet neural networks (Stanford SISL, DO-386)
- Publishes `ACASAdvisory` — `ra_active`, threat class, climb_rate_mps, heading_delta_deg
- When `acas_abort_from_advisory=true` (VTOL config), an active RA while in CRUISE triggers `abort_command`

**ACAS config:**
```yaml
rho_norm_m:     185200.0   # 100 nautical miles normalisation
v_norm_mps:     250.0      # normalisation speed
timer_period_s: 0.05       # 20 Hz evaluation
```

**Local replanner** config:
```yaml
track_deviation_threshold_m: 80.0   # deviation from nominal track to trigger replan
replan_dt_s: 0.5                    # minimum time between replans
qf_threshold: 0.65                  # quality_flag below this disables replanning
```

### 4.4 L2.4 — Health Management

**Responsibility:** Monitor system health (sensors, actuators, communication links) and publish fault events with severity classification. Trigger contingency procedures in the FSM via dedicated input atoms.

**Key nodes:**

| Node | Package | Function |
|---|---|---|
| `fdir_node` | `fdir` | Core fault detection — quality, motor, sensor timeout, C2 |
| `watchdog_node` | `fdir` | ROS2 node heartbeat monitoring (XFAIL ARCH-1.7-WATCHDOG) |
| `c2_monitor_node` | `fdir` | C2 link loss detection and contingency sequencing |
| `battery_monitor_node` | `fdir` | Battery threshold monitoring with sustain timer |

**FDIR inputs** (subscriptions from `fdir_node.py`):
- `/nav/quality_flag` — navigation quality (0..1)
- `/fmu/out/vehicle_imu` — IMU delta velocity (motor loss detection)
- `/fmu/out/vehicle_status` — PX4 arming state + hardware failure flags
- `/fmu/out/vehicle_attitude_setpoint` — thrust command (motor loss correlation)
- `/fdir/in/c2_heartbeat` — C2 link keepalive
- `/fsm/current_mode` — current FSM state (to contextualise fault response)

**FDIR outputs:**
- `/fdir/active_fault` — JSON fault name string
- `/fdir/policy_action` — policy action string (ABORT, RTB, DEGRADE, ...)
- `/fdir/emergency_landing_target` — JSON with nearest reachable landing zone

**Fault severity table** (`fdir_severity.yaml`):

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

**C2 loss contingency sequence** (EU 2019/947 Annex III):
```
C2 lost detected (c2_heartbeat_timeout_s = 1.5s)
  → link_loss_hold_s  = 30s   : hold current track
  → link_loss_rtb_s   = 30s   : initiate RTB
  → link_loss_land_s  = 120s  : emergency landing
```

**Emergency landing zones** (configured in `fdir.yaml`, ranked by glide reachability):
```yaml
emergency_landing_zones:
  - lat: 40.05  lon: -3.02  runway_m: 900   quality: 0.95
  - lat: 40.50  lon: -3.50  runway_m: 1200  quality: 0.85
  - lat: 41.20  lon: -2.00  runway_m: 800   quality: 0.70
# Reachability = glide_ratio (18) × altitude_AMSL_m
```

### 4.5 L2.5 — Vehicle Control

**Responsibility:** Translate trajectory planning outputs into flight control commands that PX4 can execute. Abstract platform differences behind the vehicle model interface.

**Key nodes:**

| Node | Package | Function |
|---|---|---|
| `trajectory_gen_node` | `trajectory_gen` | Dubins 3D waypoint follower → `TrajectorySetpoint` at 50 Hz |
| `vehicle_model_node` | `vehicle_model` | Platform envelope service — `is_feasible`, dynamic v_min |
| `mission_fsm_node` (offboard) | `mission_fsm` | Publishes `OffboardControlMode` heartbeat to PX4 when in TAKEOFF/CRUISE/EVENT/LANDING |

**Trajectory setpoint format:**
```
TrajectorySetpoint:
  position_ned[3]   # target position NED (m)
  velocity_ned[3]   # feedforward velocity NED (m/s)
```

**PX4 interface** (uXRCE-DDS, from `mission_fsm_node.py`):
- `/fmu/in/offboard_control_mode` — published at `offboard_heartbeat_hz` (default 10 Hz) while in flight states
- Position mode selected: `position=True`, all other modes `False`
- Offboard control only active in: TAKEOFF, CRUISE, EVENT, LANDING

**Vehicle model dynamic parameters** (updated per tick):
```
current_weight_kg   = MTOW - fuel_burned
v_min_ms           += v_min_reserve_gain_ms  (as fuel depletes below reserve)
turn_radius_min_m   = f(v_min_ms, bank_angle_max)
```

---

## 5. Key Message Types

All stack-internal communication uses `flightmind_msgs`:

| Message | Fields | Publisher | Subscribers |
|---|---|---|---|
| `NavigationState` | position_ned, velocity_ned, orientation_quat, covariance_6x6, quality_flag, gnss_available | navigation_bridge | mission_fsm, gpp, daidalus, acas, fdir |
| `FSMState` | current_mode, active_trigger, event_substate, go_around_count | mission_fsm | GCS telemetry, testbench |
| `DaidalusAlert` | alert_level, time_to_violation_s, min_horizontal_dist_m, num_conflict_traffic | upnext_icarous_daa | mission_fsm, local_replanner |
| `DaidalusBands` | heading_bands_deg, gs_bands_ms, vs_bands_ms, recommended_heading_deg | upnext_icarous_daa | local_replanner |
| `ACASAdvisory` | ra_active, threat_class, climb_rate_mps, heading_delta_deg, time_to_cpa_s | acas_node | mission_fsm |
| `GeofenceStatus` | violation_imminent, time_to_violation_s, zone_id | polycarp_node | mission_fsm |
| `TrafficIntruder` | intruder_id, position_ned, velocity_ned, cooperative, timestamp_s | (external ADS-B) | daidalus, acas |
| `TrajectorySetpoint` | position_ned, velocity_ned | trajectory_gen | PX4 via bridge |
| `VehicleModelState` | v_min_ms, v_max_ms, turn_radius_min_m, glide_ratio, elapsed_mission_h | vehicle_model | gpp, emergency_planner |

---

## 6. V&V Status Summary

| Domain | Total req. | Covered | Tests passing | Open gaps |
|---|---|---|---|---|
| Mission FSM | 84 | 65 (77%) | 158 passed, 23 xfail | ARCH-1.7-WATCHDOG |
| Global Planner (GPP) | 39 | 11 (28%) | 94 passed, 2 xfail | NFZ 3D altitude |
| DAIDALUS DAA | 65 | 19 (29%) | Active | Hysteresis on downgrade |
| ACAS Xu | 23 | 0 (0%) | 2 passed | .nnet integration pending |
| FDIR | 36 | 6 (17%) | 22 passed | Severity table versioning |
| Navigation Bridge | 26 | 14 (54%) | 3 passed | Battery, GPS quality sub |
| Trajectory Gen | 20 | 0 (0%) | Stub | PX4 connection pending |
| Vehicle Model | 25 | 0 (0%) | Stub | Platform adapter |
| Perception (SLAM) | — | ★ new | Stub | FAST-LIVO2 integration |
| SLZ Detector | — | ★ new | Stub | U-Net training data |

**Architecture gaps (open):**

| ID | Description | Blocker for |
|---|---|---|
| ARCH-1.7-WATCHDOG | watchdog_node not implemented — node heartbeat monitoring | HIL |
| ARCH-ACAS-NNET | ACAS Xu .nnet networks not integrated | DO-386 compliance |
| ARCH-TRAJ | trajectory_gen not connected to PX4 setpoints | HIL |
| ARCH-PERC | SLAM (FAST-LIVO2) not integrated | GNSS-denied ops |
| ARCH-SLZ | SLZ detector neural network not trained | Emergency landing |

---

## 7. Road to HIL

HIL entry criteria:
- 0 test failures (all packages)
- ≤ 15 XFAIL, all with named ARCH-X.X reference
- ARCH-ACAS-NNET closed
- ARCH-TRAJ closed (trajectory_gen publishing to PX4 SITL)
- SLAM operational in real environment (ARCH-PERC validated)

Current status: **0 failures · 23 XFAIL · 100% branch coverage on FSM · ACAS and TRAJ blocking.**

---

## 8. References

- `src/mission_fsm/mission_fsm/fsm.py` — FSM core engine
- `src/mission_fsm/mission_fsm/mission_fsm_node.py` — FSM ROS2 node
- `src/mission_fsm/config/mission_fsm.yaml` — default FSM configuration
- `src/gpp/gpp/rrt_star.py` — Informed-RRT* planner
- `src/gpp/gpp/dubins.py` — Dubins path (CSC/CCC)
- `src/fdir/fdir/fdir_node.py` — FDIR ROS2 node
- `src/fdir/config/fdir_severity.yaml` — fault severity table
- `src/navigation_bridge/navigation_bridge/navigation_bridge_node.py` — nav bridge
- `src/flightmind_msgs/msg/` — all message type definitions
- `src/mission_fsm/docs/vnv/VV_MATRIX.md` — requirements traceability
- `src/mission_fsm/docs/vnv/XFAIL_INDEX.md` — open architecture gaps
