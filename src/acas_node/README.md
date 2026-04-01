# acas_node — ACAS Xu con redes `.nnet`

Nodo **C++** (`rclcpp`) que:

- Lee **45 redes** (índice `tau_idx * 5 + prev_advisory`, con `tau` en \[0,8\] s) desde `share/acas_node/nnets/acas_xu_00.nnet` … `acas_xu_44.nnet`.
- Entradas físicas: tráfico (`flightmind_msgs/TrafficReport`, topic por defecto `/traffic/intruders`) y navegación (`flightmind_msgs/NavigationState`, `/navigation/state`). Si no hay `NavigationState`, puede usarse `/ownship/state` (`Float64MultiArray`, 6 valores) como respaldo de velocidad/rumbo.
- Publica **`/acas/advisory`** (`flightmind_msgs/ACASAdvisory`): `ra_active`, `heading_delta_deg` (velocidad de giro × `tau`), `threat_class`, etc.

## Formatos `.nnet`

- **`MODE HEURISTIC_SIL_V1`**: política SIL sintética (marcada `# SYNTHETIC-NET — replace with real .nnet for production`).
- **`MODE MLP_RELU`** + bloque `LAYERS …`: perceptrón multicapa con ReLU y capa salida lineal (5 salidas).

Ver `third_party/acas_xu_nnets/README.md` para descarga de pesos reales y normalización de entradas.

## Lanzar

```bash
ros2 run acas_node acas_node --ros-args --params-file $(ros2 pkg prefix acas_node)/share/acas_node/config/acas.yaml
```

O `ros2 launch acas_node acas_xu.launch.py`.
