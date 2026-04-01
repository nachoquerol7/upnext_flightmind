# flightmind_msgs

Mensajes ROS 2 compartidos entre los bloques del stack de autonomía Flightmind. Los nombres de topic son **contratos orientativos**; el productor/consumidor real puede mapear vía launch o bridges.

| Mensaje | Topic (referencia) | Productor típico | Consumidores típicos |
|---------|-------------------|------------------|----------------------|
| `NavigationState` | `/flightmind/navigation/state` | localización / estimación de estado | FSM, GPP, replanificador, DAA |
| `DaidalusAlert` | `/flightmind/daidalus/alert` | nodo DAIDALUS / well-clear | FSM, ACAS, monitor de misión |
| `DaidalusBands` | `/flightmind/daidalus/bands` | nodo DAIDALUS (bandas) | planificador local, visualización |
| `ACASAdvisory` | `/flightmind/acas/advisory` | nodo ACAS | bridge PX4 / comandos de evasión |
| `VehicleModelState` | `/flightmind/vehicle_model/state` | modelo de vehículo | GPP, generador de trayectorias, FSM |
| `FSMState` | `/flightmind/fsm/state` | mission FSM | planificador, telemetría, registros |
| `GeofenceStatus` | `/flightmind/geofence/status` | monitor de geocerca | FSM, Nav2 adapter, misión |
| `TrafficIntruder` | *(elemento de `TrafficReport`)* | fusión traffic | DAA, visualización |
| `TrafficReport` | `/flightmind/traffic/report` | monitor traffic / ADS-B | DAIDALUS, ACAS, FSM |

## Dependencias de interfaz

- `std_msgs` (cabeceras)
- `geometry_msgs` (declarada para extensiones futuras / tooling común)
