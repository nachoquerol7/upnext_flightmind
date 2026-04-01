# Informe Fase 0 — Setup entorno de test SIL (`mission_fsm`)

## Objetivo

Infraestructura pytest + rclpy + mocks por subsistema, sin TC funcionales M1–M10.

## Tests implementados

| Test | Descripción |
|------|-------------|
| `test_yaml_config_contains_fsm_root` | Fixture `yaml_config` carga YAML con clave `fsm`. |
| `test_fsm_params_exposes_thresholds` | Fixture `fsm_params` expone `quality_flag_threshold` del YAML. |
| `test_mock_*_spins` (×6) | Cada mock arranca, `spin_once`, destruye; aserción sobre nombre de nodo. |
| `test_mock_daidalus_inject_updates_alert` | `inject("alert_level", 2)` actualiza estado publicado. |

Los tests existentes `test_mission_fsm_transitions.py` y `test_phase0_import.py` se mantienen.

## Tests que pasan

- Todos los anteriores bajo `colcon test --packages-select mission_fsm` (sin errores de importación).

## Tests XFAIL-ARCH

- Ninguno en Fase 0.

## Decisiones de implementación

1. **`pytest-ros`**: No se añadió como dependencia ament; no hay paquete estándar homónimo en Jazzy documentado en rosdep para este workspace. Los fixtures viven en `test/conftest.py`.
2. **`mock_daidalus`**: `/daidalus/resolution_advisory` usa **`std_msgs/Float64MultiArray`** (como `daidalus_node` real), no `TwistStamped` del texto del roadmap.
3. **`mock_px4_bridge`**: Suscripción a `/fmu/in/trajectory_setpoint` solo si `px4_msgs` es importable en tiempo de test (underlay opcional). Sin px4_msgs el nodo arranca sin suscriptores (GAP documentado en código).
4. **`mock_nav2`**: Solo publicador `/plan`; servidor `/navigate_to_pose` pendiente de `nav2_msgs` (**GAP-ARCH-NAV2** en `mock_nav2.py`).
5. **`mock_fastlio2`**: Publica `/Odometry` y `/quality_flag` según roadmap; **no** existe en el código de producción actual un puente automático a `/fsm/in/quality_flag` (los tests M1+ deberán publicar en `/fsm/in/*` o añadir relay explícito en fase posterior).
6. **Fixture `ros_context`**: `shutdown` forzado si `rclpy` ya estaba ok, luego `init`/`shutdown` por test para aislar estado.

## Estructura creada

- `test/conftest.py`
- `test/mocks/mock_*.py`
- `docs/vnv/phase_0_report.md` (este fichero)
- `docs/vnv/XFAIL_INDEX.md` (plantilla)
