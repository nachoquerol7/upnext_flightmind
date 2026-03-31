# UpNext UAS workspace

Repositorio **independiente** de Autonav: simulación y stack para el hilo UpNext, con **PX4** como autopiloto. La navegación GNSS-denied y el resto de perception quedan **fuera de alcance** hasta que las volváis a priorizar.

## Contenido

| Ruta | Descripción |
|------|-------------|
| `src/upnext_bringup` | Paquete ROS 2: lanzamiento PX4 SITL (**por defecto VTOL** en Gazebo `gz`, no multicóptero). |
| `src/upnext_icarous_bridge` | Nodo puente: resuelve `ICAROUS_HOME`, comprueba `Modules/lib`, publica estado; launch **stack** = PX4 + puente. |
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
export ICAROUS_HOME="$(pwd)/third_party/icarous"
cd third_party/icarous/Modules && mkdir -p build && cd build && cmake .. && make -j"$(nproc)"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}${ICAROUS_HOME}/Modules/lib"
```

Integración ROS 2 / PX4 respecto a ICAROUS: **pendiente** (puente MAVLink o nodos propios).

## ROS 2

Requisito: ROS 2 **Jazzy** (o la distro que uséis en el equipo).

```bash
cd /path/to/upnext_uas_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

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
