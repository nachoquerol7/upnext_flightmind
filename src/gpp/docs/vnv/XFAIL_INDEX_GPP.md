# Índice XFAIL GPP

## GPP-G08 — RRT* sin garantía de mejora monótona con iteraciones
**Estado:** ABIERTO
**Tests bloqueados:** TC-RRT-012
**Descripción:** Con misma semilla, aumentar `max_iter` no garantiza menor longitud de path.

## GPP-G09 — Cota geométrica Dubins vs distancia euclidiana
**Estado:** ABIERTO
**Tests bloqueados:** SR-GPP-004
**Descripción:** La implementación actual de `dubins_length` puede devolver valores menores que la distancia euclidiana en algunos casos.

## GPP-G10 — Geofences JSON malformado en el nodo
**Estado:** CERRADO
**Fecha cierre:** 2026-04-01
**Tests bloqueados:** —
**Descripción:** `gpp_node._on_geo()` llamaba a `parse_geofences_json()` sin manejar errores de parseo.
**Cierre:** `try/except` en `_on_geo` con log de advertencia; se conserva `_nfz_json` pero no se actualizan polígonos ante JSON inválido.
