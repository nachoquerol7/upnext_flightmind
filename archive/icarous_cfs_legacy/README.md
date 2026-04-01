# ICAROUS + cFS legacy (archived)

Este directorio conserva los scripts que arrancaban **upnext_icarous_daa** con `ICAROUS_HOME` y el ecosistema cFS (`core-cpu1`, `cfe_es_startup.scr`, etc.) bajo `third_party/icarous/`.

## Estado

- **Cerrado para desarrollo nuevo:** la línea principal pasa a **DAIDALUS / PolyCARP standalone** en ROS 2 (véase `~/px4-flightmind` y `docs/AUTONOMY_ROADMAP.md` en este workspace).
- Los paquetes fuente `upnext_icarous_daa` y `upnext_icarous_bridge` **siguen en** `src/` por si hace falta consulta o migración puntual; no son la ruta recomendada.

## Cómo ejecutar un script antiguo

Desde la raíz de `upnext_uas_ws`:

```bash
source install/setup.bash
source archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh
bash archive/icarous_cfs_legacy/scripts/gui_daa_flying_demo_lite.sh
```

## Qué se movió aquí

- `setup_icarous_env.sh`, demos GUI, tests DAA que hacían `ros2 launch upnext_icarous_daa ...`, `stop_daa_demo.sh`, etc.

En `scripts/` quedan **stubs** que explican la deprecación o delegan en este directorio.
