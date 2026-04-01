# HIL / SITL — comprobación de entorno

Ejecutar antes de `ros2 launch upnext_bringup hil_sitl.launch.py`:

```bash
ls ~/PX4-Autopilot/build/px4_sitl_default/bin/px4 && echo "PX4 OK" || echo "PX4 MISSING"
which MicroXRCEAgent && echo "XRCE OK" || echo "XRCE MISSING"
```

| Componente | Rol |
|------------|-----|
| **PX4 SITL** | Binario `px4` con script de inicio POSIX (`etc/init.d-posix/rcS`). |
| **Micro-XRCE-DDS Agent** | Puente UDP (p. ej. `udp4 -p 8888`) entre PX4 y clientes DDS. |

Si falta **PX4**: clonar [PX4-Autopilot](https://github.com/PX4/PX4-Autopilot), compilar el target SITL (`make px4_sitl`), y ajustar el argumento `px4_dir` del launch si no está en `~/PX4-Autopilot`.

Si falta **MicroXRCEAgent**: instalar [eProsima Micro XRCE-DDS Agent](https://micro-xrce-dds.docs.eprosima.com/en/latest/installation.html#installing-the-agent-standalone) y asegurar que el ejecutable está en `PATH`.

En este entorno de desarrollo actual, ambas comprobaciones devolvieron **OK** (véase el log de integración).
