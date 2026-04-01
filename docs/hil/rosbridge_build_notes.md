# Rosbridge sin `sudo apt` (Jazzy)

`sudo apt install ros-jazzy-rosbridge-suite` falló en entorno sin contraseña. Se añadió **`src/rosbridge_suite`** (RobotWebTools) y se compiló en el overlay.

## Pin de versión

Rama local **`jazzy-compat-61860bf`** en el commit **`61860bf`** (anterior a `interface_base_classes` incompatible con `rosidl_pycommon` de Jazzy tal como viene en `/opt/ros/jazzy`).

La punta actual `ros2` en upstream (4.x) requiere APIs más nuevas; el pin evita `ModuleNotFoundError: rosidl_pycommon.interface_base_classes`.

## Build

```bash
source /opt/ros/jazzy/setup.bash
cd ~/upnext_uas_ws
colcon build --packages-select rosbridge_test_msgs rosbridge_msgs rosapi_msgs rosbridge_library rosapi rosbridge_server rosbridge_suite \
  --symlink-install --cmake-args -DBUILD_TESTING=OFF
```

(`BUILD_TESTING=OFF` evita la dependencia de `ament_cmake_mypy` en tests.)

## Pip adicional

El binario `rosbridge_websocket` necesita **`tornado`**. El commit anterior a “drop BSON” aún importa **`bson`** → instalar **`pymongo`** (proporciona el módulo `bson`).

```bash
pip install -r ~/upnext_uas_ws/testbench/requirements-rosbridge-pip.txt --break-system-packages
```

## Verificación

- `ros2 launch rosbridge_server rosbridge_websocket_launch.xml` → log: *Rosbridge WebSocket server started on port 9090*
- `ss -tlnp | grep 9090` → `0.0.0.0:9090`
- Cliente: `roslibpy` conecta a `localhost:9090` y lista `/fsm/state`.
