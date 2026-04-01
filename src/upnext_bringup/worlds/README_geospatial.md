# Datos geoespaciales y simulación Gazebo

Este paquete **no incluye** ortofotos, DEM ni teselas mapa-reales (tamaño y licencias). El mundo `daa_vfr_landmarks.sdf` aporta **landmarks artificiales** en el suelo para pruebas de percepción a ~200–400 m de altitud.

## Pipeline SRTM → heightmap Gazebo (incluido)

1. **Dependencias**: `python3-numpy`, `python3-pil` (o `pip install numpy Pillow`).
2. **Generar PNG + JSON** (descarga tesela SRTM1 desde viewfinderpanoramas.org, sin clave API):

   ```bash
   source install/setup.bash
   ros2 run upnext_bringup fetch_dem_heightmap -- \
     --lat 47.3769 --lon 8.5417 --half-side-m 1250 --out-size 256 \
     --prefix daa_dem_srtm --output-dir $(ros2 pkg prefix upnext_bringup)/share/upnext_bringup/worlds
   ```

   En el árbol fuente, `--output-dir` puede ser `src/upnext_bringup/worlds`. Los archivos son `daa_dem_srtm_heightmap.png` y `daa_dem_srtm_meta.json`.
3. **Ajustar** `daa_dem_srtm.sdf`: el vector `<size> X Y Z</size>` debe coincidir con **2×half-side-m** en X/Y y con **height_range_m** del JSON en Z (tras regenerar el DEM, vuelve a alinear Z).
4. **Lanzar** PX4 con `px4_gz_world:=daa_dem_srtm`. El launch copia el `.sdf` y los `daa_dem_srtm_*.png` junto al mundo de PX4.

**Opcional**: variable `OPENTOPO_API_KEY` y `--opentopo` para GeoTIFF vía OpenTopography (requiere `rasterio` para leer el TIFF).

## Integrar relieve / imágenes reales (referencias)

| Recurso | Uso típico |
|--------|------------|
| [NASA SRTM](https://www2.jpl.nasa.gov/srtm/) / [USGS EarthExplorer](https://earthexplorer.usgs.gov/) | Modelo digital de elevación (DEM) → heightmap en Gazebo (pipeline GDAL + conversión) |
| [Copernicus DEM](https://dataspace.copernicus.eu/) | DEM global, resolución media |
| [OpenStreetMap](https://www.openstreetmap.org/) | Vectores (carreteras, edificios); export → modelos o texturas (herramientas externas) |
| [Natural Earth](https://www.naturalearthdata.com/) | Datos culturales/físicos en baja resolución |
| [Gazebo Fuel](https://app.gazebosim.org/fuel/models) | Modelos de terreno/escena listos para `<include>` en `.sdf` |

## PX4 + origen geográfico

Con SITL puedes alinear el mundo con `PX4_HOME_LAT`, `PX4_HOME_LON`, `PX4_HOME_ALT` (ver init `px4-rc.gzsim` en PX4) para que `vehicle_global_position` coincida con una región real; el **relieve** sigue siendo el del `.sdf` salvo que importes un heightmap.

## Cesium / Web

**Cesium** y visores web cargan teselas y terreno ellipsoidal; **no sustituyen** la física de Gazebo. Lo habitual es: **Gazebo para dinámica**, **Cesium/Web para mapa** si comparten los mismos estados por ROS o API.
