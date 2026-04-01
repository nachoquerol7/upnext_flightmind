# Dependencias base (Fase 0)

## ROS 2 (Jazzy en Ubuntu 24.04)

```bash
sudo apt update
sudo apt install -y ros-jazzy-ompl python3-pytest python3-colcon-common-extensions
```

En Humble, sustituir `ros-jazzy-ompl` por `ros-humble-ompl`.

## PX4 SITL (verificación manual)

En el árbol PX4-Autopilot:

```bash
make px4_sitl_default jmavsim
```

Comprobar también multirrotor si aplica (`make px4_sitl gz_x500` según tu entorno).

## DAIDALUS standalone (NASA)

- Repositorio: [nasa/DAIDALUS](https://github.com/nasa/DAIDALUS) (rama / tag v2.x acorde a tu V&V).
- En este entorno ya se usa el build C++ embebido en `px4-flightmind/third_party/DAIDALUS/C++` (`make` → `lib/DAIDALUS*.a`).

## PolyCARP standalone (NASA)

- Repositorio: [nasa/PolyCARP](https://github.com/nasa/PolyCARP) — integración ROS 2 prevista en Fase 4 (`polycarp_node`).

## Utilidades Python opcionales (Fase 5 DEM)

```bash
pip install elevation
```

## Script

```bash
./scripts/install_deps_phase0.sh
```

Instala solo paquetes APT conocidos; no clona NASA automáticamente.
