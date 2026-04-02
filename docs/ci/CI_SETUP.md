# CI: workflow SIL V&V (`sil_vnv.yml`)

## Qué hace

En cada **push** o **pull request** a `main`, el job **`sil-tests`**:

1. Usa **Ubuntu 24.04** (Noble). Los paquetes apt **`ros-jazzy-*`** oficiales están publicados para Noble; **Ubuntu 22.04 (Jammy) no tiene** `ros-jazzy-desktop` en `packages.ros.org`, por eso el workflow no usa `ubuntu-22.04`.
2. Instala **ROS 2 Jazzy** (`ros-jazzy-desktop`), **colcon**, **`ros-jazzy-px4-msgs`** (necesario para compilar/importar `navigation_bridge` en tests).
3. Instala **pytest** y **pytest-cov** con pip (`--break-system-packages`, entorno GitHub Actions).
4. **Compila** el cierre mínimo: `--packages-up-to mission_fsm`, `navigation_bridge`, `acas_node` y **`gpp`** (es `exec_depend` de `mission_fsm` y no siempre se incluye solo con `up-to mission_fsm`).
5. **Ejecuta tests**: `mission_fsm`, `gpp`, `navigation_bridge`, `acas_node` con **`--return-code-on-test-failure`**.
6. Vuelve a ejecutar tests de **`mission_fsm`** con cobertura de **`mission_fsm.fsm`** y genera **`coverage.xml`** en la raíz del repositorio.
7. Sube **`coverage.xml`** como artifact (**`mission-fsm-fsm-coverage`**).

## Cómo leer la salida en GitHub

1. Abre la pestaña **Actions** del repositorio.
2. Elige el workflow **“SIL V&V”** y la ejecución concreta.
3. Dentro, el job **`sil-tests`** muestra los pasos colapsables:
   - **Build SIL closure**: errores de CMake / dependencias faltantes.
   - **Test SIL suite**: salida de pytest/gtest por paquete.
   - **Coverage**: segunda pasada de `mission_fsm` con `--cov`.
4. En **Summary** → **Artifacts** descarga `mission-fsm-fsm-coverage` si necesitas el XML para Sonar, Codecov, etc.

## XFAIL vs FAIL (pytest)

| Marca | Significado |
|-------|-------------|
| **PASSED** | El test cumplió las aserciones. |
| **XFAIL** | Test marcado como *esperado fallo* (`@pytest.mark.xfail`). **No cuenta como fallo del job**: el código bajo prueba puede ser conocidamente incompleto; el CI sigue verde si no hay FAIL reales. |
| **FAIL** | Fallo real: aserción rota o excepción no esperada. Con **`--return-code-on-test-failure`**, **colcon test** devuelve código ≠ 0 y el workflow **falla**. |
| **ERROR** | Suele ser fallo en *setup* del test (imports, fixtures, colección). Trata como **fallo de CI** hasta corregirlo. |

Objetivo del workflow: **permitir XFAIL**, **no permitir FAIL/ERROR** no esperados.

## Reproducir localmente (mismo espíritu que CI)

En una máquina con **Jazzy** instalado por apt (idealmente Ubuntu 24.04):

```bash
cd /ruta/al/clon/upnext_flightmind   # o upnext_uas_ws
source /opt/ros/jazzy/setup.bash
# Si px4_msgs no viene en el desktop: sudo apt install ros-jazzy-px4-msgs
pip install --user pytest pytest-cov   # o --break-system-packages si usas el Python del sistema

colcon build --symlink-install \
  --packages-up-to mission_fsm \
  --packages-up-to navigation_bridge \
  --packages-up-to acas_node \
  --packages-up-to gpp

source install/setup.bash
colcon test \
  --packages-select mission_fsm gpp navigation_bridge acas_node \
  --return-code-on-test-failure \
  --event-handlers console_direct+ \
  --executor sequential
colcon test-result --verbose
```

Cobertura `mission_fsm.fsm` (opcional):

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon test \
  --packages-select mission_fsm \
  --return-code-on-test-failure \
  --event-handlers console_direct+ \
  --executor sequential \
  --pytest-args --cov=mission_fsm.fsm --cov-report=xml:"$PWD/coverage.xml" --cov-branch
colcon test-result --verbose
```

## Relación con `ci.yml`

- **`ci.yml`**: build más amplio, `rosdep`, submódulos, más paquetes.
- **`sil_vnv.yml`**: foco **SIL / testbench**: menos paquetes, más rápido, falla explícitamente si rompes la suite SIL.

Ambos pueden convivir; la badge de SIL apunta solo a `sil_vnv.yml`.
