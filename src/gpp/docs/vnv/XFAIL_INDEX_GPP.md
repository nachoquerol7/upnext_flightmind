# Índice XFAIL GPP

## GPP-G07 — Dubins start==goal no retorna ~0 siempre
**Estado:** ABIERTO
**Tests bloqueados:** TC-DUB-003
**Descripción:** `dubins_length` puede devolver longitud no nula en casos degenerados con mismo estado inicial/final.

## GPP-G08 — RRT* sin garantía de mejora monótona con iteraciones
**Estado:** ABIERTO
**Tests bloqueados:** TC-RRT-012
**Descripción:** Con misma semilla, aumentar `max_iter` no garantiza menor longitud de path.

## GPP-G09 — Cota geométrica Dubins vs distancia euclidiana
**Estado:** ABIERTO
**Tests bloqueados:** SR-GPP-004
**Descripción:** La implementación actual de `dubins_length` puede devolver valores menores que la distancia euclidiana en algunos casos.
