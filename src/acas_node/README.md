# acas_node (Fase 8 — ACAS Xu proceso RT)

Capa simplificada tipo **ACAS Xu** en proceso **independiente** del planificador: solo escucha **ownship** y **tráfico**, calcula un RA tabular y, si hay conflicto, publica en **`/fmu/in/trajectory_setpoint`**. Sin suscripciones a GPP, replanificador ni trayectoria nominal.

## Prioridad en tiempo real

El launch `acas_xu.launch.py` arranca el nodo con:

`chrt -f 80 …`

Eso pide **SCHED_FIFO** prioridad 80. Sin permisos adecuados fallará (típico: `Operation not permitted`).

- En desarrollo: ejecutar el launch con **`sudo`** o dar al usuario capacidad **`CAP_SYS_NICE`** (p. ej. `sudo setcap cap_sys_nice+ep` sobre el intérprete, consciente de implicaciones de seguridad).
- Sin RT: quitar el `prefix` del `Node` en el launch o lanzar solo `ros2 run acas_node acas_node`.

El mensaje `TrajectorySetpoint` de PX4 **no incluye un campo de “prioridad”**; la prioridad operativa viene del **proceso RT** + heurística de **no publicar** al FC cuando no hay RA (no interfiere con el pipeline nominal).

## Topics

| Dirección | Topic | Tipo |
|-----------|--------|------|
| Sub | `/ownship/state` | `Float64MultiArray` (≥6: n,e,z_ned,vn,ve,vd) |
| Sub | `/traffic/intruders` | `flightmind_msgs/TrafficReport` |
| Pub | `/acas/ra_active` | `Bool` |
| Pub | `/acas/resolution_advisory` | `Float64MultiArray` [climb_rate_mps, heading_delta_deg] |
| Pub | `/fmu/in/trajectory_setpoint` | `px4_msgs/TrajectorySetpoint` **solo si** `ra_active` |

## Parámetros (YAML `config/acas.yaml`)

- `tau_ca`: umbral de tiempo hasta conflicto (s).
- `dmod_ca`: distancia horizontal mínima de CA (m).
- `z_sep_m`: separación vertical para filtrar amenazas (m).
- `ra_climb_rate_mps`: magnitud RA vertical (m/s, positivo = subir en sentido aeronáutico).
- `ra_heading_delta_deg`: delta de rumbo para maniobra lateral (deg, positivo = giro a la derecha visto desde arriba).

Dependencia: **`px4_msgs`** en overlay o underlay (véase README raíz del workspace).
