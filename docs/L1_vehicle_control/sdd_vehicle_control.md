# sdd_vehicle_control.md

**Document ID:** FM-SDD-L2.5  
**Version:** 1.0  
**Date:** 2026-04-02  
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext Spain  
**Status:** Draft

---

## 1. Purpose

This domain translates trajectory planning decisions into flight control commands that PX4 can execute. It abstracts platform differences behind the vehicle model interface, ensuring the rest of the stack remains platform-agnostic.

---

## 2. Domain Decomposition

```
L2.5 — Vehicle Control
├── vehicle_model      (pkg: vehicle_model)
│   └── platform_adapter   (internal — per-platform parameter sets)
├── trajectory_gen     (pkg: trajectory_gen)
└── PX4 interface      (uXRCE-DDS bridge — external)
```

**Why trajectory_gen is canonical here and not in Trajectory Planning:** The trajectory_gen node's primary consumer is PX4 — it publishes `TrajectorySetpoint` directly to the flight controller. Its function is *execution*, not *planning*. The Global Planner produces a route (waypoints); trajectory_gen converts that route into continuous setpoints at 50 Hz. That is a control function, not a planning function.

**platform_adapter is internal to vehicle_model:** There is no separate `platform_adapter` node. Platform-specific parameters (v_min, v_max, turn_radius, glide_ratio) are loaded from YAML into the vehicle_model node at startup. The abstraction is a parameter set, not a software component.

---

## 3. Subsystem: vehicle_model

### 3.1 Function

Maintains the current aircraft flight envelope and provides feasibility checks to planning algorithms. Accounts for dynamic changes to the envelope (fuel burn reducing MTOW, increasing v_min).

### 3.2 Implementation

- **ROS2 node:** `src/vehicle_model/vehicle_model/vehicle_model_node.py`
- **Model core:** `src/vehicle_model/vehicle_model/model.py`
- **Config:** `src/vehicle_model/config/vehicle_model.yaml`

### 3.3 Envelope parameters

```yaml
# vehicle_model.yaml — fixed-wing proxy (all platforms use this as baseline)
v_min_ms:              30.0    # minimum airspeed (m/s)
v_max_ms:              57.0    # maximum airspeed (m/s)
turn_radius_min_m:     600.0   # minimum Dubins turn radius
climb_rate_max_ms:     8.0     # maximum climb rate (m/s)
descent_rate_max_ms:   5.0     # maximum descent rate (m/s)
glide_ratio:           18.0    # horizontal/vertical glide distance ratio
mtow_kg:               750.0   # maximum take-off weight (kg)
fuel_mass_initial_kg:  120.0   # initial fuel mass
fuel_burn_kgh:         50.0    # fuel burn rate (kg/h)
v_min_reserve_gain_ms: 5.0     # v_min increase per fuel reserve step
```

### 3.4 Dynamic envelope

As fuel burns, the aircraft becomes lighter but the minimum airspeed constraint increases operationally (closer to structural limits at lower weight):

```python
# From model.py — dynamic v_min update
current_weight_kg = mtow_kg - fuel_burned_kg
# v_min increases as fuel reserve drops below threshold
v_min_effective = v_min_ms + v_min_reserve_gain_ms * reserve_factor
```

### 3.5 Platform abstraction

Different platforms load different parameter sets at launch. The stack code never has platform-specific branches — only the YAML changes:

| Platform | turn_radius_min_m | v_min_ms | glide_ratio |
|---|---|---|---|
| Fixed-wing (default) | 600.0 | 30.0 | 18.0 |
| VTOL (transition) | 200.0 | 20.0 | 12.0 |
| Helicopter | 50.0 | 0.0 | 4.0 |
| MALE | 800.0 | 35.0 | 22.0 |

These are configured via the `config_file` parameter at launch — no code changes required between platforms.

### 3.6 is_feasible

The vehicle_model exposes a feasibility check used by the Global Planner and emergency_planner:

```python
def is_feasible(path: List[Waypoint], state: VehicleModelState) -> bool:
    # Checks: turn radius, climb/descent rates, airspeed bounds
    # Returns False if any waypoint transition violates envelope
```

### 3.7 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/navigation/state` | `flightmind_msgs/NavigationState` | navigation_bridge |
| `/fdir/active_fault` | `std_msgs/String` | fdir |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/vehicle_model/state` | `flightmind_msgs/VehicleModelState` | 10 Hz |

```
VehicleModelState:
  header
  float64 current_weight_kg
  float64 v_min_ms              # current dynamic minimum
  float64 v_max_ms
  float64 turn_radius_min_m
  float64 climb_rate_max_mps
  float64 descent_rate_max_mps
  float64 glide_ratio
  float64 elapsed_mission_h
```

### 3.8 V&V status

- Stub — phase 1 tests passing (import, parameter loading)
- `test_vehicle_model_phase1.py` passing
- Functional tests pending — `is_feasible` not yet wired to GPP
- Open: ARCH-VM — vehicle_model not connected to GPP path validation

---

## 4. Subsystem: trajectory_gen

### 4.1 Function

Converts the discrete waypoint path from the Global Planner into a continuous stream of `TrajectorySetpoint` messages at 50 Hz for PX4 to track. Uses Dubins 3D curves to interpolate between waypoints with altitude profiles.

### 4.2 Implementation

- **ROS2 node:** `src/trajectory_gen/trajectory_gen/trajectory_gen_node.py`
- **3D Dubins:** `src/trajectory_gen/trajectory_gen/dubins3d.py`
- **Waypoint follower:** `src/trajectory_gen/trajectory_gen/waypoint_follower.py`

### 4.3 Algorithm: Dubins 3D

Extends the 2D Dubins path (used by GPP) to 3D by adding altitude profile interpolation:

```
dubins3d(start, goal, rho, climb_rate, descent_rate)
  → sequence of (n, e, d, heading) at uniform arc-length steps
```

The altitude profile is computed separately from the horizontal path — altitude changes linearly along the arc length, clamped to `climb_rate_max_mps` and `descent_rate_max_mps` from the vehicle model.

**Why Dubins 3D over a full 3D planner:** The horizontal NFZ avoidance is handled by the Global Planner (RRT* with Dubins edges). The trajectory_gen only needs to interpolate between already-valid waypoints. A full 3D replanner here would duplicate the GPP function and add unnecessary complexity.

### 4.4 Waypoint follower

The `WaypointFollower` tracks progress along the current path:
- Advances to the next waypoint when within `waypoint_capture_radius_m`
- Handles the final waypoint (goal reached → publishes `takeoff_complete` or `land_command`)
- Republishes the current setpoint at 50 Hz regardless of path update rate

### 4.5 PX4 interface

`trajectory_gen_node` publishes `TrajectorySetpoint` which is forwarded to PX4 via the uXRCE-DDS bridge. The FSM node independently publishes `OffboardControlMode` heartbeat to keep PX4 in offboard mode:

```python
# From mission_fsm_node.py — offboard heartbeat
# Active only in: TAKEOFF, CRUISE, EVENT, LANDING
msg = OffboardControlMode()
msg.position = True   # position control mode
msg.velocity = False
# Published at offboard_heartbeat_hz (default 10 Hz)
```

**Current status:** trajectory_gen → PX4 connection is **ARCH-TRAJ** — open gap, HIL blocker. The node exists and publishes setpoints, but the uXRCE-DDS bridge is not configured to forward them to a real PX4 instance.

### 4.6 Interfaces

**Subscriptions:**

| Topic | Type | Source |
|---|---|---|
| `/gpp/global_path` | `nav_msgs/Path` | global_planner |
| `/navigation/state` | `flightmind_msgs/NavigationState` | navigation_bridge |
| `/vehicle_model/state` | `flightmind_msgs/VehicleModelState` | vehicle_model |
| `/fsm/state` | `flightmind_msgs/FSMState` | mission_fsm |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/trajectory/setpoint` | `flightmind_msgs/TrajectorySetpoint` | 50 Hz |
| `/fsm/in/takeoff_complete` | `std_msgs/Bool` | Event |
| `/fsm/in/touchdown` | `std_msgs/Bool` | Event |
| `/gpp/takeoff_state` | `std_msgs/Float64MultiArray` | 10 Hz |

```
TrajectorySetpoint:
  header
  float64[3] position_ned   # north, east, down (m)
  float64[3] velocity_ned   # feedforward vn, ve, vd (m/s)
```

### 4.7 V&V status

- Phase 0 (import) and waypoint tests passing
- `test_trajectory_waypoints.py`, `test_traj_phase7.py` passing
- **ARCH-TRAJ open** — not connected to PX4 — HIL blocker
- Full integration tests pending

---

## 5. Design Decisions and Rationale

### 5.1 Why 50 Hz setpoint rate

PX4 requires offboard setpoints at a minimum rate to stay in offboard mode (typically > 2 Hz). 50 Hz matches the `navigation_bridge` publication rate, ensuring setpoints use the freshest position estimate. Lower rates would introduce lag in trajectory tracking.

### 5.2 Why position control mode over velocity

Position control (`OffboardControlMode.position = True`) is more robust to communication latency. If a setpoint is delayed or lost, PX4 holds the last commanded position rather than continuing on a velocity vector. This is a conservative choice appropriate for a safety-critical system.

### 5.3 Why vehicle_model is separate from trajectory_gen

The vehicle model is consumed by three different planning functions: GPP (turn radius, v_min for Dubins), emergency_planner (glide_ratio for LZ reachability), and trajectory_gen (climb/descent rates). If it were internal to trajectory_gen, the other planners would have no access to envelope data. A shared service is the correct pattern.

### 5.4 Why platform_adapter is internal state, not a separate node

Platform adaptation is purely parametric — different YAML values, same code. A separate `platform_adapter` node would add a ROS2 process, a topic, and a QoS contract for what is essentially a configuration lookup. The parameter is loaded once at startup and published as part of `VehicleModelState`. Adding a node for this would be over-engineering.

---

## 6. Known Limitations and Open Gaps

| Gap | Description | Impact |
|---|---|---|
| ARCH-TRAJ | trajectory_gen not connected to PX4 SITL | Cannot fly autonomously — HIL blocker |
| ARCH-VM | vehicle_model not wired to GPP `is_feasible` | Routes not validated against envelope |
| Altitude profile | Dubins 3D altitude interpolation not validated with real platform | Climb rates may exceed envelope limits |
| Platform params | VTOL/helicopter/MALE envelope params not validated | Default fixed-wing proxy used for all platforms |

---

## 7. References

- `src/vehicle_model/vehicle_model/vehicle_model_node.py`
- `src/vehicle_model/vehicle_model/model.py`
- `src/vehicle_model/config/vehicle_model.yaml`
- `src/trajectory_gen/trajectory_gen/trajectory_gen_node.py`
- `src/trajectory_gen/trajectory_gen/dubins3d.py`
- `src/trajectory_gen/trajectory_gen/waypoint_follower.py`
- `src/mission_fsm/mission_fsm/mission_fsm_node.py` — offboard heartbeat
- `src/flightmind_msgs/msg/TrajectorySetpoint.msg`
- `src/flightmind_msgs/msg/VehicleModelState.msg`
