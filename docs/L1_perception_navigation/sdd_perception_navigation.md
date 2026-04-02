# Perception & Navigation — System Design Description
**FM-SDD-01 · v1.0 · 2026-04-02**
**Status:** active
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext

---

## 1. Purpose

Provides robust Position, Navigation and Timing (PNT) in GNSS-denied environments via multi-sensor fusion (LiDAR + Camera + IMU). Publishes `NavigationState` to the rest of the stack at 50 Hz. Detects Safe Landing Zones (SLZ) using terrain geometry and synthetic DEM analysis.

---

## 2. BDD [L1 → L2]

```
Perception & Navigation [L1]
  + goal: GNSS-denied PNT · SLZ detection
  + std: DO-365 · SORA
  │
  ├── L2: slam_engine            (pkg: perception_bridge)
  │     + FAST-LIVO2 target · LiDAR+Cam+IMU · stub active
  │     + 50 Hz pose output
  │
  ├── L2: navigation_bridge      (pkg: navigation_bridge)
  │     + EKF2 adapter · quality_flag · SLAM override arbitration
  │     + 50 Hz RELIABLE+TRANSIENT_LOCAL
  │
  └── L2: landing_zone_detector  (pkg: slz_detector)
        + SyntheticDEM + geometric scoring
        + U-Net target (stub active)
        + 5 Hz candidates output
```

---

## 3. L2 Blocks

| Block | Package | Key outputs | Freq | Status |
|---|---|---|---|---|
| slam_engine | perception_bridge | /slam/pose · /slam/quality · /slam/map · /nav/quality_override | 50 Hz | stub — FAST-LIVO2 pending |
| navigation_bridge | navigation_bridge | /navigation/state · /nav/quality_flag | 50 Hz RELIABLE+TL | ✓ 5 passed |
| landing_zone_detector | slz_detector | /slz/candidates · /slz/best · /slz/status | 5 Hz | ✓ 7 passed — DEM geometric |

---

## 4. Data Flow

```
[PX4 EKF2]
/fmu/out/vehicle_odometry
        │
        ▼
navigation_bridge_node
  covariance c0 → quality_flag thresholds:
    c0 < 0.3  → 1.0
    c0 < 0.7  → 0.7
    c0 >= 0.7 → 0.3
        │
        │◄── /nav/quality_override (from slam_engine, max arbitration, timeout 2.0s)
        │
        ▼
/navigation/state (NavigationState, 50Hz RELIABLE+TRANSIENT_LOCAL)
/nav/quality_flag (Float64, 50Hz)

[Sensors]
/scan (PointCloud2) ──┐
/imu/data (Imu) ──────┤
                       ▼
              slam_node (perception_bridge)
              IMU integration: orientation/velocity/position
              Point cloud quality: density + centroid distance
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
/slam/pose      /slam/quality   /nav/quality_override
(50Hz)          (50Hz)          (50Hz → navigation_bridge)
                       │
                       ▼
              /slam/map (PointCloud2, accumulated, up to 2000 pts)
                       │
                       ▼
              slz_node (slz_detector)
              Cell segmentation 3x3m
              Geometric score: flatness + density
              DEM score: slope + roughness (SyntheticDEM)
              Final score = 0.5 × geometric + 0.5 × dem
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
/slz/candidates  /slz/best      /slz/status
(PoseArray)     (PoseStamped)   (JSON string)
        │
        ▼
FSM atom: slz_available
(score > 0.6 AND age < 5s)
→ enables ABORT→LANDING emergency transition
```

---

## 5. slam_engine (pkg: perception_bridge)

### Subscriptions

| Topic | Type | Purpose |
|---|---|---|
| `/scan` | `sensor_msgs/PointCloud2` | LiDAR point cloud input |
| `/imu/data` | `sensor_msgs/Imu` | IMU angular velocity + linear acceleration |

### Publications

| Topic | Type | Freq | QoS |
|---|---|---|---|
| `/slam/pose` | `geometry_msgs/PoseWithCovarianceStamped` | 50 Hz | RELIABLE |
| `/slam/quality` | `std_msgs/Float64` | 50 Hz | BEST_EFFORT |
| `/slam/map` | `sensor_msgs/PointCloud2` | 50 Hz | BEST_EFFORT |
| `/nav/quality_override` | `std_msgs/Float64` | 50 Hz | BEST_EFFORT |

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `slam_backend` | `'stub'` | Backend selector. 'stub' = geometric IMU. Future: 'fast_livo2' |
| `fixed_pose_x` | `0.0` | Stub initial position N (m) |
| `fixed_pose_y` | `0.0` | Stub initial position E (m) |
| `fixed_pose_z` | `100.0` | Stub initial altitude (m) |
| `pose_covariance_diag` | `[0.1]*6` | Stub covariance diagonal |

### Quality Computation

Quality from point cloud:
- `density_score` = min(n_points / 500, 1.0) — normalised point count
- `centroid_distance` = mean distance from centroid (proxy for cloud spread)
- `quality = clip(density_score * (1 - centroid_distance/50), 0, 1)`

Quality thresholds → `/nav/quality_override`:
- quality > 5.0 covariance proxy → 0.3
- quality > 1.0 → 0.7
- quality ≤ 1.0 → 1.0

### Implemented vs Stub

| Component | Status |
|---|---|
| IMU integration (orientation, velocity, position) | ✓ Real |
| Point cloud quality metric (density + centroid) | ✓ Real |
| point_cloud_utils.py (serialise/deserialise PointCloud2) | ✓ Real |
| FAST-LIVO2 backend | ✗ Stub — warning logged |
| EKF2 fusion | ✗ Not implemented |

---

## 6. navigation_bridge (pkg: navigation_bridge)

### Subscriptions

| Topic | Type | Purpose |
|---|---|---|
| `/fmu/out/vehicle_odometry` | `px4_msgs/VehicleOdometry` | PX4 EKF2 odometry |
| `/nav/quality_override` | `std_msgs/Float64` | SLAM quality override |

### Publications

| Topic | Type | Freq | QoS |
|---|---|---|---|
| `/navigation/state` | `flightmind_msgs/NavigationState` | 50 Hz | RELIABLE+TRANSIENT_LOCAL |
| `/nav/quality_flag` | `std_msgs/Float64` | 50 Hz | RELIABLE |
| `/fsm/in/quality_flag` | `std_msgs/Float64` | 50 Hz (via relay) | RELIABLE |

### Quality Flag Arbitration

```python
if slam_override_fresh (age <= slam_override_timeout_sec):
    quality_flag = max(ekf2_quality, slam_override)
else:
    quality_flag = ekf2_quality  # EKF2 only

# EKF2 quality from covariance c0 = position_variance[0]:
# c0 < 0.3  → 1.0
# c0 < 0.7  → 0.7 (was > 1.0 in threshold mapping)
# c0 >= 0.7 → 0.3
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `slam_override_timeout_sec` | `2.0` | Max age of slam override before falling back to EKF2 |
| `odom_timeout_sec` | `1.0` | No odometry → quality_flag = 0.0 |

### Tests

| TC | Description | Result |
|---|---|---|
| TC-NAV-BRIDGE-001 | Node starts and publishes /navigation/state | PASS |
| TC-NAV-BRIDGE-002 | quality_flag computed from odometry covariance | PASS |
| TC-NAV-BRIDGE-003 | quality_flag = 0.0 on stale odometry | PASS |
| TC-NAV-BRIDGE-004 | quality_flag rises when valid SLAM override arrives | PASS |
| TC-NAV-BRIDGE-005 | quality_flag falls back to EKF2 when override expires | PASS |

---

## 7. landing_zone_detector (pkg: slz_detector)

### Subscriptions

| Topic | Type | Purpose |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | Camera image (semantic classifier input — stub) |
| `/slam/map` | `sensor_msgs/PointCloud2` | 3D point cloud map from SLAM |

### Publications

| Topic | Type | Freq | QoS |
|---|---|---|---|
| `/slz/candidates` | `geometry_msgs/PoseArray` | 5 Hz | RELIABLE |
| `/slz/best` | `geometry_msgs/PoseStamped` | 5 Hz | RELIABLE |
| `/slz/status` | `std_msgs/String` (JSON) | 5 Hz | BEST_EFFORT |

### /slz/status JSON Schema

```json
{
  "n_candidates": 3,
  "best_score": 0.82,
  "best_ned": [10.5, -3.2, 0.0],
  "dem_slope_deg": 1.4,
  "dem_roughness": 0.3
}
```

### Scoring Pipeline

```
For each 3x3m cell in /slam/map:
  1. geometric_score:
       flatness   = 1 - clip(std(Z) / 2.0, 0, 1)   weight 0.7
       density    = clip(n_points / 9.0, 0, 1)       weight 0.3
       geometric  = 0.7 * flatness + 0.3 * density

  2. dem_score (SyntheticDEM):
       slope_score     = 1 - clip(slope_deg / 15.0, 0, 1)   weight 0.6
       roughness_score = 1 - clip(roughness / 2.0, 0, 1)    weight 0.4
       dem = 0.6 * slope + 0.4 * roughness

  3. final_score = 0.5 * geometric + 0.5 * dem

Top 3 cells by score → /slz/candidates
Best cell → /slz/best
```

### SyntheticDEM

Reproducible terrain (seed=42) for SIL determinism:
- **Flat zone** (central, radius ~100m): elevation uniform ±0.3m — ideal SLZ
- **Gaussian hills** (3-5): amplitude 20-50m
- **Background noise**: sigma=1.5m

Methods: `get_elevation(n,e)`, `get_slope_deg(n,e)`, `get_roughness(n,e,r)`, `get_flat_zones(slope_threshold_deg=5.0)`

### TerrainClassifier

| Method | Implementation | Status |
|---|---|---|
| `classify(image) -> float` | Returns 0.8 (stub) | Stub — U-Net pending |
| `classify_from_dem(n, e, dem) -> float` | slope+roughness scoring | ✓ Real |

### Tests

| TC | Description | Result |
|---|---|---|
| TC-SLZ-001 | Flat terrain gives score > 0.8 | PASS |
| TC-SLZ-002 | Irregular terrain gives score < 0.4 | PASS |
| TC-SLZ-003 | ≥1 candidate published when map received | PASS |
| TC-SLZ-004 | Central DEM zone has score > 0.8 | PASS |
| TC-SLZ-005 | Gaussian hill has score < 0.3 | PASS |
| TC-SLZ-006 | best_score > 0.7 with flat map | PASS |
| cloud_io roundtrip | PointCloud2 XYZ serialise/deserialise | PASS |

---

## 8. FSM Integration

The `slz_available` atom in mission_fsm is derived from `/slz/best`:
- `True` when `/slz/best` has been published within the last 5s AND `best_score > 0.6`
- Enables the emergency landing transition:

```yaml
- from: ABORT
  to: LANDING
  trigger: abort_slz_emergency_land
  when:
    all: [slz_available, fdir_emergency]
```

---

## 9. Open Gaps

| ID | Description | HIL blocker |
|---|---|---|
| ARCH-PERC | FAST-LIVO2 not integrated — stub only | Yes |
| ARCH-SLZ | U-Net semantic classifier not trained | No |
| ARCH-1.8 | Pose jump detection not implemented | No |
| NAV-019 | battery_remaining_pct from PX4 battery_status | No |
| ARCH-BRIDGE | /nav/quality_override → /fsm/in/quality_flag relay | No |
