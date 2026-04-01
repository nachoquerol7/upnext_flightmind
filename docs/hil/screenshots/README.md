# Capturas del testbench visual (HIL / SITL)

En esta máquina, **`ros-jazzy-rosbridge-suite` no estaba instalado** y `sudo apt install` no pudo ejecutarse de forma no interactiva, por lo que **no se generó PNG automático** en la sesión de integración.

Para obtener una captura local:

1. Instalar rosbridge: `sudo apt install ros-jazzy-rosbridge-suite -y`
2. Con PX4 + XRCE + `mission_fsm` ya en marcha, arrancar solo el puente WebSocket:
   ```bash
   bash ~/upnext_uas_ws/testbench/start_rosbridge_only.sh
   ```
3. Abrir `~/upnext_uas_ws/testbench/index.html` en Firefox (o `xdg-open`).
4. Comprobar indicador **verde** (“ROS2 connected”) y ejecutar la secuencia de misión.
5. Capturar:
   ```bash
   scrot ~/Desktop/testbench_demo_$(date +%Y%m%d_%H%M%S).png
   ```
6. Copiar el PNG a esta carpeta y commitear.

**Nota sobre DAIDALUS:** `mission_fsm` consume **`/fsm/in/daidalus_alert`** (`Int32`), no `/daidalus/alert_level`. Para ver EVENT en el testbench, publicar en `/fsm/in/daidalus_alert` o añadir un nodo relay.
