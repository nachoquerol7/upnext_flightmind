# Flightmind Autonomy Stack — System Design Description
**FM-SDD-00 · v1.0 · 2026-04-02**
**Status:** active
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext Spain, Getafe

---

## 1. System Overview

Flightmind is the autonomy stack for BVLOS UAS operations developed by UpNext / Airbus UpNext. It coordinates perception, navigation, detect-and-avoid, path planning, and mission management under DO-178C DAL-C and EU 2019/947.

| Field | Value |
|---|---|
| Hardware target | PX4 Autopilot · ROS2 Jazzy · Jetson Orin 16GB (inference) · Intel NUC 12 (compute) |
| ROS distro | ROS2 Jazzy (Ubuntu 24.04 LTS) |
| Flight controller | PX4 Autopilot via uXRCE-DDS bridge |
| Workspace | `~/upnext_uas_ws` |
| Next milestone | Demo — 8 April 2026 |

---

## 2. Functional Decomposition [L0 → L1]

```
Flightmind [L0]
  + mission: BVLOS autonomous UAS operations
  + hw: PX4 + Jetson Orin 16GB + Intel NUC 12
  + std: DO-178C DAL-C · DO-365 · ARP4754A · EU 2019/947
  │
  ├── L1: Perception & Navigation    (GNSS-denied PNT · SLAM · SLZ)
  ├── L1: Trajectory Planning        (9-state HFSM · Informed-RRT* · trajectory)
  ├── L1: Collision Avoidance        (DAIDALUS · ACAS Xu · PolyCARP)
  ├── L1: Health Management          (FDIR · watchdog · C2 · battery)
  ├── L1: Vehicle Control            (vehicle envelope · Dubins 3D · PX4)
  └── L1: V&V                        (SIL · CI · requirements traceability)
```

---

## 3. L1 Domain Allocation

| Domain | Responsibility | Standards | Status |
|---|---|---|---|
| Perception & Navigation | GNSS-denied PNT · multi-sensor fusion · SLZ detection | DO-365 · SORA | active |
| Trajectory Planning | 9-state HFSM · Informed-RRT* GPP · trajectory setpoints | DO-178C DAL-C | active |
| Collision Avoidance | DAIDALUS traffic separation · ACAS Xu · PolyCARP geofence | DO-365 · DO-386 | active |
| Health Management | Fault detection · isolation · recovery · C2 contingency | ARP4754A §6 | active |
| Vehicle Control | Vehicle envelope · Dubins 3D trajectory · PX4 setpoints | — | dev |
| V&V | SIL test suite · CI pipeline · requirements traceability | DO-178C · ARP4754A | 297/320 req |

---

## 4. L2 Package Mapping

| Package (code) | Architecture name | Domain | Tests |
|---|---|---|---|
| `perception_bridge` | slam_engine | Perception & Navigation | 4 passed |
| `navigation_bridge` | navigation_bridge | Perception & Navigation | 5 passed |
| `slz_detector` | landing_zone_detector | Perception & Navigation | 7 passed |
| `mission_fsm` | mission_fsm | Trajectory Planning | 158 passed · 23 xfailed |
| `gpp` | global_planner | Trajectory Planning | 94 passed · 2 xfailed |
| `trajectory_gen` | trajectory_gen | Vehicle Control | 3 passed |
| `vehicle_model` | vehicle_model | Vehicle Control | 2 passed |
| `upnext_icarous_daa` | DAIDALUS | Collision Avoidance | active |
| `acas_node` | ACAS Xu | Collision Avoidance | 2 passed |
| `local_replanner` | local_replanner | Collision Avoidance | dev |
| `upnext_airspace` + `polycarp_node` | airspace_monitor | Collision Avoidance | active |
| `fdir` | fdir + c2_monitor + battery_monitor | Health Management | 22 passed |

> Package names do not match architecture names — intentional, rename planned post-demo.
> In documents: use architecture name with `(pkg: xxx)` in parentheses.

---

## 5. V&V Status

| Package | Passed | XFailed | Failed |
|---|---|---|---|
| mission_fsm | 158 | 23 | 0 |
| gpp | 94 | 2 | 0 |
| fdir | 22 | 0 | 0 |
| acas_node | 2 | 0 | 0 |
| navigation_bridge | 5 | 0 | 0 |
| perception_bridge | 4 | 0 | 0 |
| slz_detector | 7 | 0 | 0 |
| trajectory_gen | 3 | 0 | 0 |
| vehicle_model | 2 | 0 | 0 |
| **Total** | **297** | **25** | **0** |

**HIL entry criteria:** 0 failures · ≤15 XFAIL · ARCH-ACAS-NNET closed · ARCH-TRAJ closed · ARCH-PERC validated.

---

## 6. Open Architecture Gaps

| ID | Description | HIL blocker |
|---|---|---|
| ARCH-1.7-WATCHDOG | watchdog_node not implemented in fdir | Yes |
| ARCH-ACAS-NNET | ACAS Xu .nnet neural networks not integrated | Yes |
| ARCH-TRAJ | trajectory_gen not connected to PX4 setpoints | Yes |
| ARCH-PERC | FAST-LIVO2 SLAM not integrated — geometric stub only | Yes |
| ARCH-SLZ | SLZ U-Net semantic model not trained | No |
| ARCH-FDIR-SEV | Severity table not versioned, combined faults not modelled | No |
| ARCH-VM | vehicle_model not wired to GPP is_feasible | No |
| ARCH-1.3 | EVENT substate not exposed in /fsm/current_mode | No |
| ARCH-1.8 | Pose jump detection not implemented | No |
| ARCH-1.9 | Interrupt waypoint not persisted for resumption | No |
| ARCH-1.10 | Black-box logging / replay not implemented | No |
| ARCH-DAI-RECOVERY | DAIDALUS RECOVERY level (4) not mapped in FSM | No |
| ARCH-DAI-FEED | DAIDALUS feed timeout not implemented | No |
| ARCH-BRIDGE | Subsystem topic bridge to /fsm/in/* not integrated | No |

---

## 7. Closed Architecture Decisions

| Decision | Rationale |
|---|---|
| trajectory_gen canonical in Vehicle Control | Consumer is PX4, not the planner. Execution ≠ planning. |
| platform_adapter internal to vehicle_model | Pure parameter set, not a node. YAML config only. |
| emergency_planner internal to local_replanner | Activates only in response to CA events. Not standalone. |
| airspace_monitor in Collision Avoidance | Output is a threat signal (ABORT atom), not a navigation estimate. |
| watchdog internal to fdir | Same package, shared config, no separate ROS2 node warranted. |
| FSM first-match transitions | Explicit auditable priority. YAML order = priority order. DO-178C friendly. |
| NFZ as hard constraints in RRT* | Safety requirement, not cost. Penalties can always be traded off. |
| quality_flag as scalar | Single consistent signal across all consumers. Full covariance in NavigationState if needed. |
| BEST_EFFORT QoS for VehicleOdometry | Stale odometry worse than no odometry. Freshness > reliability at 50Hz. |
| Static LZ + dynamic SLZ | Static zones = guaranteed fallback. SLZ = enhancement, not dependency. |
| YAML-driven FSM | Platform variants without code forks. DO-178C: config changes, not code changes. |

---

## 8. Applicable Standards

| Standard | Domain |
|---|---|
| DO-178C DAL-C | Mission FSM — 100% branch coverage |
| DO-365 | DAIDALUS DAA |
| DO-386 | ACAS Xu |
| ARP4754A §6 | FDIR functional hazard assessment |
| EU 2019/947 Annex III | C2 loss contingency · BVLOS |
| SORA | Specific Operations Risk Assessment |
| ROS2 REP 103 | Coordinate frames (NED) |
| STANAG 4671 | UAS airworthiness baseline |
| STANAG 4586 | C2 link |

---

## 9. Message Types (flightmind_msgs)

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
