# Collision Avoidance — System Design Description
**FM-SDD-03 · v1.0 · 2026-04-02**
**Status:** active
**Classification:** CONFIDENTIAL — UpNext / Airbus UpNext

---

## 1. Purpose

Ensures traffic separation and airspace compliance using DAIDALUS v2 (DO-365), ACAS Xu (DO-386) and PolyCARP geofence monitoring. Publishes alert levels and resolution bands to the Mission FSM and GPP.

---

## 2. BDD [L1 → L2]

```
Collision Avoidance [L1]
  + goal: traffic separation · airspace compliance
  + std: DO-365 · DO-386
  │
  ├── L2: DAIDALUS          (pkg: upnext_icarous_daa)
  │     + NASA v2 · DO-365 · 4 alert levels
  │     + heading/speed/altitude bands 360°
  │
  ├── L2: ACAS Xu           (pkg: acas_node)
  │     + DO-386 · HorizontalCAS .nnet
  │     + last-resort advisory (TMOD ≤ 35s)
  │
  ├── L2: local_replanner   (pkg: local_replanner)
  │     + tactical evasion · emergency_planner internal
  │     + dev
  │
  └── L2: airspace_monitor  (pkg: upnext_airspace + polycarp_node)
        + PolyCARP NASA Langley · NFZ 3D
        + violation_imminent → FSM geofence_breach
```

---

## 3. L2 Blocks

| Block | Package | Key outputs | Freq | Status |
|---|---|---|---|---|
| DAIDALUS | upnext_icarous_daa | /daidalus/alert · /daidalus/alert_level · /daidalus/bands | event-driven | active |
| ACAS Xu | acas_node | /acas/advisory · ra_active · abort_command | event-driven | 2 passed |
| local_replanner | local_replanner | tactical setpoints | — | dev |
| airspace_monitor | upnext_airspace + polycarp_node | /polycarp/geofence_status · violation_imminent | 10 Hz | active |

---

## 4. DAIDALUS Alert Levels

| Level | Name | FSM Response | Hysteresis |
|---|---|---|---|
| 0 | NONE | — | — |
| 1 | FAR | Hysteresis count starts (daidalus_alert_amber=1) | Yes |
| 2 | MID | `daidalus_escalated` → EVENT (after escalate_ticks=2) | Yes |
| 3 | NEAR | `daidalus_near` → EVENT immediately | **No** (fast-path) |
| 4 | RECOVERY | `daidalus_recovery` → allows return toward CRUISE | XFAIL ARCH-DAI-RECOVERY |

### 4.1 FSM Escalation Logic

```python
# In MissionFsm.step() — builtins:
daidalus_escalated = (alert >= daidalus_alert_amber)  # sustained for escalate_ticks=2
daidalus_near      = (alert == 3)                      # immediate, no hysteresis
daidalus_recovery  = (alert >= 4)                      # XFAIL — no explicit mapping yet
```

### 4.2 DAIDALUS Bands

Published on `/daidalus/bands` (DaidalusBands):
```
heading_bands_deg[]    # unsafe heading ranges [from, to]
gs_bands_ms[]          # unsafe ground speed ranges
vs_bands_ms[]          # unsafe vertical speed ranges
recommended_heading_deg
```

GPP consumes bands to avoid forbidden headings during replanning.

---

## 5. ACAS Xu

ACAS Xu acts only when Time to Minimum separation (TMOD) ≤ 35s — the last line of defence when DAIDALUS no longer has time for a planned resolution.

### 5.1 Architecture

```
acas_node (C++)
  input:  /traffic/intruders (TrafficIntruder[])
          /navigation/state (NavigationState)
  output: /acas/advisory (ACASAdvisory)
          /acas/ra_active (Bool)
          → abort_command when threat_class == 3
```

### 5.2 ACASAdvisory Message

```
ACASAdvisory:
  ra_active:          bool
  threat_class:       uint8  # 0=clear · 1=advisory · 2=corrective · 3=emergency
  climb_rate_mps:     float32
  heading_delta_deg:  float32
  time_to_cpa_s:      float32
```

### 5.3 Neural Network

- Algorithm: HorizontalCAS — table-lookup approximated by `.nnet` neural network
- Network: 5 inputs (relative state) → 5 advisory outputs
- Status: XFAIL ARCH-ACAS-NNET — `.nnet` weights not integrated, stub active

### 5.4 DAIDALUS vs ACAS Xu — Why Both

| | DAIDALUS | ACAS Xu |
|---|---|---|
| Activation horizon | ~55s | TMOD ≤ 35s |
| Resolution type | Preventive + corrective bands | Emergency manoeuvre |
| Multi-traffic | Yes | No (ownship + primary threat) |
| Output | Bands → GPP replanning | Direct advisory → trajectory_gen |
| DO standard | DO-365 | DO-386 |

They are **complementary layers**, not alternatives. Removing DAIDALUS and relying only on ACAS Xu would mean always arriving at the emergency threshold — equivalent to having no brakes until the last metre.

---

## 6. Airspace Monitor (PolyCARP)

### 6.1 Purpose

Monitors whether the planned trajectory crosses any active NFZ using PolyCARP (NASA Langley). Publishes `violation_imminent` which drives the `geofence_breach` atom in the FSM.

### 6.2 FSM Integration

```
/polycarp/violation_imminent (Bool)
  → navigation_bridge_node
  → /fsm/in/geofence_breach (Bool)
  → geofence_breach atom (sustained 0.5s → ABORT)
```

### 6.3 NFZ Format

3D polygon zones from GeoJSON. Loaded at startup, dynamic updates via `/airspace/update`.

---

## 7. Key Requirements

| ID | Description | Status |
|---|---|---|
| DAA-001 | 4 alert levels NONE/FAR/MID/NEAR per DO-365 §2.2 | CUBIERTO |
| DAA-014 | Total latency alert → FSM transition < 100ms P99 | CUBIERTO |
| DAA-052 | Escalate to ACAS when alert_level = NEAR (3) | CUBIERTO |
| DAA-016 | Heading bands continuous 360° with sector classification | PARCIAL |
| AIR-001 | PolyCARP NASA Langley as containment engine | CUBIERTO |
| AIR-014 | violation_imminent published when trajectory crosses NFZ | CUBIERTO |
| DAA-011 | Hysteresis on alert downgrade | XFAIL ARCH-DAI-RECOVERY |

---

## 8. Open Gaps

| ID | Description | HIL blocker |
|---|---|---|
| ARCH-ACAS-NNET | ACAS Xu .nnet weights not integrated | Yes |
| ARCH-DAI-RECOVERY | DAIDALUS RECOVERY level (4) not mapped | No |
| ARCH-DAI-FEED | DAIDALUS feed timeout not implemented | No |
| ARCH-DAI-ADV | Advisory consumption and validation incomplete | No |
| local_replanner | Tactical evasion not implemented | No |
