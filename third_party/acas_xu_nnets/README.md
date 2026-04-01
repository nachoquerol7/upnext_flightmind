# ACAS Xu `.nnet` weights (HorizontalCAS / Stanford)

Este directorio está preparado para alojar las **45 redes** del estilo HorizontalCAS (índice `tau × prev_advisory`).

## Descarga (red corporativa / CI)

Desde la raíz del workspace:

```bash
mkdir -p ~/upnext_uas_ws/third_party/acas_xu_nets
cd ~/upnext_uas_ws/third_party/acas_xu_nets
wget -q "https://raw.githubusercontent.com/sisl/HorizontalCAS/master/GenerateNetworks/networks/HCAS_rect_v6_pra{0..4}_tau{00..08}_25HU_3000it.nnet" 2>/dev/null || true
```

Si la descarga falla, el paquete `acas_node` incluye redes **sintéticas** en `src/acas_node/nnets/` generadas con `generate_synthetic_nnets.py` (política `HEURISTIC_SIL_V1`, marcadas `# SYNTHETIC-NET — replace with real .nnet for production`).

## Normalización de entradas (referencia HorizontalCAS / ACAS Xu)

Las redes esperan entradas acotadas; en `acas_node` se normalizan así (por defecto, parametrizable vía YAML):

| Entrada | Significado | Normalización por defecto |
|--------|-------------|---------------------------|
| `rho` | Distancia horizontal al intruso (m) | `rho / rho_norm_m` → \[0,1\] |
| `theta` | Ángulo relativo al rumbo propio (rad) | `theta / π` → \[-1,1\] |
| `psi` | Rumbo relativo del intruso (rad) | `psi / π` → \[-1,1\] |
| `v_own` | Velocidad horizontal propia (m/s) | `v / v_norm_mps` → \[0,1\] |
| `v_int` | Velocidad horizontal intruso (m/s) | `v / v_norm_mps` → \[0,1\] |

Valores por defecto: `rho_norm_m = 185200`, `v_norm_mps = 250` (ajustables a los rangos documentados en el README del repositorio HorizontalCAS cuando uses redes reales).
