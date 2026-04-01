# Capturas del testbench visual (HIL / SITL)

## Sesión 2026-04-01 — rosbridge operativo (desde fuente)

- **Rosbridge** compilado en el workspace (véase `../rosbridge_build_notes.md`); **no** hizo falta `sudo apt install ros-jazzy-rosbridge-suite`.
- **Puerto 9090:** confirmado con `ss -tlnp | grep 9090` (listener `python3` en `0.0.0.0:9090`).
- **Conexión tipo testbench:** `roslibpy.Ros(host='localhost', port=9090)` → `is_connected: True`, `/fsm/state` presente en el grafo.
- **Firefox / indicador verde:** no comprobado en esta sesión automatizada (no se lanzó el navegador). Con `index.html` apuntando a `ws://localhost:9090`, el comportamiento esperado es indicador **verde** si el WebSocket enlaza.

**PNG:** no se generó archivo en esta carpeta: faltan `import` (ImageMagick) y `scrot` sin `sudo apt`. Instalar uno de ellos y capturar manualmente, o copiar desde el escritorio.

**DAIDALUS:** usar **`/fsm/in/daidalus_alert`** (`Int32`), no `/daidalus/alert_level`, para forzar EVENT en `mission_fsm`.
