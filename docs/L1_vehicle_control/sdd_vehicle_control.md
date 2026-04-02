# Vehicle Control — System Design Description
**FM-SDD-05 · v1.0 · 2026-04-02**
**Status:** dev
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext

---

## 1. Purpose

Manages the vehicle physical envelope and executes trajectory setpoints from the global planner via Dubins 3D curves at 50 Hz, interfacing directly with PX4 via uXRCE-DDS in Offboard mode.

---

## 2. BDD [L1 → L2]

```
Vehicle Control [L1]
  + goal: trajectory execution · envelope enforcement · PX4 interface
  │
  ├── L2: vehicle_model     (pkg: vehicle_model)
  │     + envelope parameters · platform_adapter (internal)
  │     + 2 passed · dev
  │
  └── L2: trajectory_gen    (pkg: trajectory_gen)
        + Dubins 3D · Pure Pursuit · 50Hz setpoints
        + PX4 Offboard mode heartbeat
        + 3 passed · ARCH-TRAJ open
```

---

## 3. Vehicle Envelope (default fixed-wing proxy)

Defined in `vehicle_model/config/vehicle_model.yaml`:

| Parameter | Value | Unit |
|---|---|---|
| `v_min_ms` | 30.0 | m/s |
| `v_max_ms` | 57.0 | m/s |
| `turn_radius_min_m` | 600.0 | m |
| `climb_rate_max_mps` | 8.0 | m/s |
| `descent_rate_max_mps` | 5.0 | m/s |
| `glide_ratio` | 18.0 | — |
| `MTOW_kg` | 750.0 | kg |
| `fuel_mass_initial_kg` | 120.0 | kg |
| `fuel_burn_kgh` | 50.0 | kg/h |
| `v_min_reserve_gain_ms` | 5.0 | m/s (v_min increase as fuel depletes) |

Platform variants are pure parameter sets in YAML — no code forks needed.

### VehicleModelState Message

```
VehicleModelState:
  current_weight_kg:    float32
  v_min_ms:             float32   # dynamic: increases as fuel depletes
  v_max_ms:             float32
  turn_radius_min_m:    float32
  glide_ratio:          float32
  elapsed_mission_h:    float32
```

Published at 10 Hz on `/vehicle_model/state`.

---

## 4. Trajectory Generator (pkg: trajectory_gen)

### 4.1 Subscriptions

| Topic | Type | Purpose |
|---|---|---|
| `/gpp/path` | `nav_msgs/Path` | Global path from GPP |
| `/navigation/state` | `flightmind_msgs/NavigationState` | Current position for Pure Pursuit |

### 4.2 Publications

| Topic | Type | Freq | QoS |
|---|---|---|---|
| `/trajectory/setpoint` | `flightmind_msgs/TrajectorySetpoint` | 50 Hz | RELIABLE |
| `/fmu/in/trajectory_setpoint` | `px4_msgs/TrajectorySetpoint` | 50 Hz | BEST_EFFORT |
| `/fmu/in/offboard_control_mode` | `px4_msgs/OffboardControlMode` | 10 Hz | BEST_EFFORT |

### 4.3 Pure Pursuit Algorithm

```
1. Resample GPP polyline (nav_msgs/Path poses) to uniform steps ~1m
2. Each tick: find look-ahead point at 2-3m along polyline from current position
3. Compute arc to intercept look-ahead from current heading
4. Publish setpoint toward look-ahead point
5. If no valid path or NaN in setpoint: publish Hold
   Hold = current NED position, velocity = [0,0,0]
```

### 4.4 PX4 Offboard Mode

PX4 requires `OffboardControlMode` heartbeat at ≥ 2 Hz before accepting setpoints. trajectory_gen publishes at 10 Hz when FSM is in TAKEOFF, CRUISE, EVENT or LANDING:

```python
OffboardControlMode:
  position: True
  velocity: False
  acceleration: False
  attitude: False
  body_rate: False
```

Timestamp synchronisation: ROS nanoseconds // 1000 → PX4 microseconds.

### 4.5 Hold Behaviour

If path is invalid, empty, or contains NaN:
- `_sanitize_ned()` clamps NaN to current position
- `_publish_hold()` publishes current NED at velocity zero
- Prevents NaN from reaching PX4 EKF2 (which would cause divergence)

### 4.6 Open Gap: ARCH-TRAJ

The dual publisher (flightmind_msgs + px4_msgs) is implemented. What is **not yet connected**:
- PX4 SITL is not running alongside the stack in SIL tests
- The setpoints reach the topic but PX4 is not listening
- Integration test with live PX4 SITL pending

**HIL blocker: Yes.**

---

## 5. Key Requirements

| ID | Description | Status |
|---|---|---|
| TRAJ-001 | Trajectory setpoints published at 50 Hz | CUBIERTO (stub) |
| TRAJ-002 | OffboardControlMode published at 10 Hz in flight states | CUBIERTO |
| TRAJ-003 | Hold on invalid path — never publish NaN to PX4 | CUBIERTO |
| TRAJ-004 | Pure Pursuit look-ahead 2-3m configurable | CUBIERTO |
| TRAJ-005 | Dubins turn radius = vehicle_model.turn_radius_min_m | PENDIENTE (ARCH-VM) |

---

## 6. Open Gaps

| ID | Description | HIL blocker |
|---|---|---|
| ARCH-TRAJ | trajectory_gen not connected to PX4 SITL | Yes |
| ARCH-VM | vehicle_model not wired to GPP is_feasible check | No |
