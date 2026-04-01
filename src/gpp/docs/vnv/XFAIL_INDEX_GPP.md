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
**Estado:** ABIERTO
**Tests bloqueados:** TC-GEO-012 (parte ROS en `test_tc_geo_012_gpp_node_survives_malformed_geofences_json`)
**Descripción:** `gpp_node._on_geo()` llama a `parse_geofences_json()` sin `try/except`; un `JSONDecodeError` puede propagarse y abortar el procesamiento del executor.
