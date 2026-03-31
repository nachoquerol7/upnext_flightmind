# UpNext UAS workspace

Repositorio **independiente** de Autonav: simulación y stack para el hilo UpNext, con **PX4** como autopiloto. La navegación GNSS-denied y el resto de perception quedan **fuera de alcance** hasta que las volváis a priorizar.

## Contenido

| Ruta | Descripción |
|------|-------------|
| `src/upnext_bringup` | Paquete ROS 2: lanzamiento PX4 SITL (**por defecto VTOL** en Gazebo `gz`, no multicóptero). |
| `src/upnext_icarous_bridge` | Nodo Python: comprueba `ICAROUS_HOME` / `Modules/lib`. |
| `src/upnext_icarous_daa` | Nodo C++ **`daa_traffic_monitor_node`**: enlaza `libTrafficMonitor` (DAIDALUS) con topics **PX4** `vehicle_global_position` + `vehicle_local_position`; intruso sintético NED opcional; publica `~/daa/bands_summary`. |
| `src/upnext_airspace` | **GeoJSON** de zonas restringidas (`config/`), **`airspace_viz_node`** (RViz `MarkerArray` en `map`, alineado NED PX4), **`airspace_monitor_node`** (bool + id si `lat/lon/alt` dentro de polígono). |
| `third_party/icarous` | Submódulo **NASA ICAROUS** (DAIDALUS, PolyCARP, módulos Core). |

## Clonar

```bash
git clone --recurse-submodules <url-del-repo> upnext_uas_ws
cd upnext_uas_ws
```

Si ya clonaste sin submódulos:

```bash
git submodule update --init --recursive
cd third_party/icarous && bash UpdateModules.sh && cd ../..
```

`UpdateModules.sh` descarga dependencias NASA (cFE, etc.) necesarias para compilar ICAROUS según su documentación.

## ICAROUS (compilación rápida)

Ver `third_party/icarous/docs/compiling.md`. Resumen:

```bash
source scripts/setup_icarous_env.sh
cd third_party/icarous && bash UpdateModules.sh
cd Modules && mkdir -p build && cd build && cmake .. && make -j"$(nproc)"
```

Tras compilar, `Modules/lib` contiene las `.so` (ACCoRD/DAIDALUS, TrafficMonitor, etc.). `source scripts/setup_icarous_env.sh` exporta `ICAROUS_HOME` y `LD_LIBRARY_PATH` (opcional; el binario `daa_traffic_monitor_node` lleva `RPATH` a `Modules/lib`).

## ROS 2

Requisito: ROS 2 **Jazzy** (o la distro que uséis en el equipo).

**Dependencia:** `px4_msgs` debe estar en el mismo overlay o en un underlay (p. ej. `~/ros2_ws`).

```bash
cd /path/to/upnext_uas_ws
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash   # px4_msgs
colcon build --symlink-install
source install/setup.bash
```

### ICAROUS + PX4 (DAIDALUS en bucle)

Con **uXRCE/Micro XRCE-DDS** en marcha (PX4 publicando en ROS 2):

```bash
# Solo el monitor DAA (sin lanzar PX4 desde aquí)
ros2 launch upnext_icarous_daa daa_traffic_monitor.launch.py
```

PX4 SITL + DAA en un solo launch:

```bash
ros2 launch upnext_icarous_daa daa_stack.launch.py
```

Topics por defecto: `/fmu/out/vehicle_global_position`, `/fmu/out/vehicle_local_position`. Parámetros: `intruder_n_m`, `intruder_e_m`, `intruder_enable`, etc.

### Offboard en conflicto DAA (opcional)

`daa_traffic_monitor_node` puede publicar en **`/fmu/in/offboard_control_mode`** y **`/fmu/in/trajectory_setpoint`** cuando DAIDALUS detecta tráfico en conflicto (`numConflictTraffic` ≥ `conflict_traffic_min`): mantiene **x/y** y pide **subida** en NED (`resolution_climb_m` en metros).

- Por defecto **`offboard_enable:=false`** (no manda nada al FCU).
- Activar: `offboard_enable:=true` (o `ros2 launch upnext_icarous_daa daa_stack_offboard.launch.py`).
- **Solo simulación / pruebas**: en vuelo real hace falta caso de seguridad, modos y frecuencia offboard según PX4.
- En PX4 hace falta **modo OFFBOARD**, **arming** y stream de setpoints acorde a la documentación (p. ej. `COM_OBL_RC_ACT`, `COM_RC_OVERRIDE`, etc., según versión).

Cuando el conflicto cesa, el nodo **deja de publicar** setpoints; recupera el control manualmente o con otro nodo.

### Espacio aéreo restringido (GeoJSON + RViz)

- Ejemplo: `src/upnext_airspace/config/restricted_zones_sample.geojson` (solo demo; no operacional).
- `ros2 launch upnext_airspace airspace_demo.launch.py` — visualización + monitor (este último usa `px4_msgs` y `/fmu/out/vehicle_global_position`).
- RViz2: Fixed Frame **`map`**, topic de markers bajo el namespace del nodo `airspace_viz`.
- Origen del plano: por defecto **centroide** de los polígonos; para alinear con home EKF: `use_centroid_origin:=false` y `origin_lat_deg` / `origin_lon_deg`.
- Script plantilla para descargar datos: `scripts/fetch_geojson_example.sh` (añade URL y licencia válida).

## PX4 SITL (VTOL por defecto)

Necesitas un clon de **PX4-Autopilot** con simulación **Gazebo Harmonic** según [documentación PX4](https://docs.px4.io/).

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch upnext_bringup px4_sitl.launch.py
```

Solo puente ICAROUS (sin PX4): `ros2 run upnext_icarous_bridge icarous_bridge_node`

PX4 + puente: `ros2 launch upnext_icarous_bridge upnext_stack.launch.py`

Parámetros útiles:

- `px4_dir:=/ruta/a/PX4-Autopilot`
- `vehicle:=gz_x500` — multicóptero si queréis comparar
- `vehicle:=gz_plane` — ala fija (si está disponible en vuestra versión de PX4)

El objetivo por defecto `gz_standard_vtol` sustituye el enfoque “solo quad” del otro repo.

## Publicar en Git (sin `gh` en esta máquina)

Si aún no tienes remoto:

```bash
cd ~/upnext_uas_ws
git remote add origin https://github.com/<usuario>/<repo>.git
git push -u origin main
```

Copia portable del repo (un solo fichero):

```bash
git bundle create ~/upnext_uas_ws.bundle --all
```

En otro PC: `git clone upnext_uas_ws.bundle upnext_uas_ws`

## Licencia

Paquetes propios: Apache-2.0. **ICAROUS**: NASA Open Source Agreement (`third_party/icarous/LICENSES`).
