#!/usr/bin/env python3
"""
Descarga una tesela SRTM (1 arc-seg) desde viewfinderpanoramas.org/dem1,
recorta alrededor de un punto y genera un PNG en escala de grises para
<heightmap> en Gazebo + metadatos JSON.

Requisitos: numpy, Pillow (python3-pil), red para HTTPS.

Alternativa con API: OPENTOPO_API_KEY + --opentopo para GeoTIFF (GDAL opcional).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Tuple

import numpy as np

try:
    from PIL import Image
except ImportError as e:
    raise SystemExit(
        'Falta Pillow: sudo apt install python3-pil o pip install Pillow'
    ) from e

# Espejo estable para SRTM1 (HGT 3601×3601) — no requiere clave.
VFP_DEM1_URL = 'https://viewfinderpanoramas.org/dem1/{tile}.zip'


def srtm_tile_name(lat: float, lon: float) -> str:
    """Nombre de tesela SRTM (esquina SO): N47E008, N37W122, etc."""
    lat_i = int(math.floor(lat))
    lon_i = int(math.floor(lon))
    ns = 'N' if lat_i >= 0 else 'S'
    ew = 'E' if lon_i >= 0 else 'W'
    return f'{ns}{abs(lat_i):02d}{ew}{abs(lon_i):03d}'


def latlon_to_rc_srtm1(lat: float, lon: float, lat0: int, lon0: int) -> Tuple[int, int]:
    """
    Índices fila/columna en HGT SRTM1 (3601×3601).
    Fila 0 = borde norte de la tesela; columna 0 = borde oeste.
    """
    row = int(np.clip(np.round((lat0 + 1 - lat) * 3600), 0, 3600))
    col = int(np.clip(np.round((lon - lon0) * 3600), 0, 3600))
    return row, col


def meters_to_deg(lat0_rad: float, dn_m: float, de_m: float) -> Tuple[float, float]:
    """Delta lat/lon (grados) aproximados desde desplazamiento N/E en metros."""
    dlat = dn_m / 111_320.0
    dlon = de_m / (111_320.0 * max(math.cos(lat0_rad), 0.01))
    return dlat, dlon


def read_hgt(path: Path, size: int = 3601) -> np.ndarray:
    """Lee .hgt SRTM (int16 BE)."""
    raw = path.read_bytes()
    expected = size * size * 2
    if len(raw) != expected:
        raise ValueError(f'HGT tamaño inesperado: {len(raw)} != {expected}')
    arr = np.frombuffer(raw, dtype='>i2').reshape(size, size).astype(np.float32)
    arr[arr <= -32_000] = np.nan
    return arr


def download_dem1_zip(tile: str, dest_dir: Path) -> Path:
    url = VFP_DEM1_URL.format(tile=tile)
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f'{tile}.zip'
    req = urllib.request.Request(url, headers={'User-Agent': 'upnext_bringup-fetch_dem/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        zip_path.write_bytes(r.read())
    return zip_path


def extract_hgt(zip_path: Path, work: Path) -> Path:
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.hgt')]
        if not names:
            raise RuntimeError('ZIP sin .hgt')
        zf.extract(names[0], path=work)
        return work / names[0]


def crop_and_resample(
    hgt: np.ndarray,
    row0: int,
    row1: int,
    col0: int,
    col1: int,
    out_size: int,
) -> Tuple[np.ndarray, float, float]:
    """Recorta [row0:row1, col0:col1], reescala a out_size×out_size; devuelve elevación MSL min/max."""
    patch = hgt[row0:row1, col0:col1]
    if patch.size == 0:
        raise ValueError('Recorte vacío (revisa lat/lon y tamaño).')
    valid = np.isfinite(patch)
    if not np.any(valid):
        raise ValueError('Recorte sin datos válidos (mar / void).')
    zmin = float(np.nanmin(patch))
    zmax = float(np.nanmax(patch))
    # Rellenar voids con mínimo local para exportar imagen
    filled = np.where(valid, patch, zmin)
    img = Image.fromarray(filled.astype(np.float64))
    img = img.resize((out_size, out_size), Image.Resampling.BILINEAR)
    arr = np.array(img, dtype=np.float32)
    return arr, zmin, zmax


def to_heightmap_png(z: np.ndarray, zmin: float, zmax: float) -> np.ndarray:
    """Normaliza a uint8 0..255 (0 = mínimo terreno, 255 = máximo)."""
    span = max(zmax - zmin, 1.0)
    u = (z - zmin) / span
    u = np.clip(u, 0.0, 1.0)
    return (u * 255.0).astype(np.uint8)


def fetch_opentopo_geotiff(
    south: float,
    north: float,
    west: float,
    east: float,
    api_key: str,
    dest: Path,
) -> None:
    """Descarga GeoTIFF vía OpenTopography globaldem (requiere OPENTOPO_API_KEY)."""
    q = (
        f'https://portal.opentopography.org/API/globaldem?'
        f'demtype=SRTMGL3&south={south}&north={north}&west={west}&east={east}'
        f'&outputFormat=GTiff&API_Key={api_key}'
    )
    req = urllib.request.Request(q, headers={'User-Agent': 'upnext_bringup-fetch_dem/1.0'})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    if data[:4] == b'<?xm' or data[:5] == b'<?xml':
        raise RuntimeError(
            'OpenTopography devolvió error XML (clave/rate limit). Usa modo VFP por defecto.'
        )
    dest.write_bytes(data)


def run_vfp_pipeline(
    center_lat: float,
    center_lon: float,
    half_side_m: float,
    out_size: int,
    work: Path,
) -> Tuple[np.ndarray, dict]:
    if center_lat < 0:
        raise NotImplementedError(
            'v1: solo latitud ≥ 0 (hemisferio norte). Ampliación SRTM sur pendiente.'
        )
    lat0 = int(math.floor(center_lat))
    lon0 = int(math.floor(center_lon))
    tile = srtm_tile_name(center_lat, center_lon)
    # Comprobar que el bbox cabe en una tesela
    lat_rad = math.radians(center_lat)
    dlat, dlon = meters_to_deg(lat_rad, half_side_m, half_side_m)
    south = center_lat - dlat
    north = center_lat + dlat
    west = center_lon - dlon
    east = center_lon + dlon
    corners = [(south, west), (south, east), (north, west), (north, east)]
    for la, lo in corners:
        if int(math.floor(la)) != lat0 or int(math.floor(lo)) != lon0:
            raise NotImplementedError(
                'El recorte cruza teselas SRTM. Reduce --half-side-m o implementa empalme.'
            )

    zip_path = download_dem1_zip(tile, work)
    hgt_path = extract_hgt(zip_path, work)
    hgt = read_hgt(hgt_path)

    rows: list[int] = []
    cols: list[int] = []
    for la, lo in ((north, west), (north, east), (south, west), (south, east)):
        r, c = latlon_to_rc_srtm1(la, lo, lat0, lon0)
        rows.append(r)
        cols.append(c)
    r0, r1 = min(rows), max(rows)
    c0, c1 = min(cols), max(cols)
    r0 = max(0, r0)
    r1 = min(3600, r1)
    c0 = max(0, c0)
    c1 = min(3600, c1)

    zpatch, zmin, zmax = crop_and_resample(hgt, r0, r1 + 1, c0, c1 + 1, out_size)
    meta = {
        'source': 'viewfinderpanoramas_dem1',
        'tile': tile,
        'center_lat': center_lat,
        'center_lon': center_lon,
        'half_side_m': half_side_m,
        'bbox_deg': {'south': south, 'north': north, 'west': west, 'east': east},
        'elevation_msl_min': zmin,
        'elevation_msl_max': zmax,
        'height_range_m': max(zmax - zmin, 1.0),
        'horizontal_size_m': 2.0 * half_side_m,
        'out_pixels': out_size,
    }
    return zpatch, meta


def write_outputs(
    zpatch: np.ndarray,
    meta: dict,
    png_path: Path,
    json_path: Path,
) -> None:
    zmin = float(np.min(zpatch))
    zmax = float(np.max(zpatch))
    png_arr = to_heightmap_png(zpatch, zmin, zmax)
    Image.fromarray(png_arr, mode='L').save(png_path)
    meta['height_range_m'] = max(zmax - zmin, 1.0)
    meta['png_path'] = png_path.name
    json_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser(
        description='SRTM → PNG heightmap para Gazebo (upnext_bringup).'
    )
    ap.add_argument('--lat', type=float, default=47.3769, help='Latitud centro (WGS84)')
    ap.add_argument('--lon', type=float, default=8.5417, help='Longitud centro')
    ap.add_argument(
        '--half-side-m',
        type=float,
        default=1250.0,
        help='Mitad del lado del cuadrado horizontal (m); lado total = 2× esto.',
    )
    ap.add_argument(
        '--out-size',
        type=int,
        default=256,
        help='Tamaño de salida (px); potencias de 2 ayudan al render.',
    )
    ap.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Directorio de salida (por defecto: share/upnext_bringup/worlds si existe ament).',
    )
    ap.add_argument(
        '--prefix',
        type=str,
        default='daa_dem_srtm',
        help='Prefijo de archivos: <prefix>_heightmap.png y <prefix>_meta.json',
    )
    ap.add_argument(
        '--opentopo',
        action='store_true',
        help='Usar OpenTopography API (SRTMGL3) en lugar de VFP; requiere OPENTOPO_API_KEY.',
    )
    args = ap.parse_args()

    out_dir = args.output_dir
    if out_dir is None:
        try:
            from ament_index_python.packages import get_package_share_directory

            out_dir = Path(get_package_share_directory('upnext_bringup')) / 'worlds'
        except Exception:
            out_dir = Path(__file__).resolve().parent.parent / 'worlds'
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / f'{args.prefix}_heightmap.png'
    json_path = out_dir / f'{args.prefix}_meta.json'

    if args.opentopo:
        key = os.environ.get('OPENTOPO_API_KEY', '').strip()
        if not key:
            print('Define OPENTOPO_API_KEY o pasa --opentopo sin usar (usa VFP).', file=sys.stderr)
            return 1
        lat_rad = math.radians(args.lat)
        dlat, dlon = meters_to_deg(lat_rad, args.half_side_m, args.half_side_m)
        south, north = args.lat - dlat, args.lat + dlat
        west, east = args.lon - dlon, args.lon + dlon
        tif = out_dir / '_opentopo_raw.tif'
        fetch_opentopo_geotiff(south, north, west, east, key, tif)
        # GDAL opcional: rasterio/gdal_translate → numpy
        try:
            import rasterio  # type: ignore

            with rasterio.open(tif) as ds:
                band = ds.read(1).astype(np.float32)
                band[band == ds.nodata] = np.nan
                zmin = float(np.nanmin(band))
                zmax = float(np.nanmax(band))
                img = Image.fromarray(band)
                img = img.resize((args.out_size, args.out_size), Image.Resampling.BILINEAR)
                zpatch = np.array(img, dtype=np.float32)
        except ImportError:
            print(
                'Modo --opentopo requiere rasterio (pip install rasterio) para leer el GeoTIFF.',
                file=sys.stderr,
            )
            return 1
        meta = {
            'source': 'opentopography_srtmgl3',
            'center_lat': args.lat,
            'center_lon': args.lon,
            'half_side_m': args.half_side_m,
            'bbox_deg': {'south': south, 'north': north, 'west': west, 'east': east},
            'elevation_msl_min': zmin,
            'elevation_msl_max': zmax,
            'height_range_m': max(zmax - zmin, 1.0),
            'horizontal_size_m': 2.0 * args.half_side_m,
            'out_pixels': args.out_size,
        }
        write_outputs(zpatch, meta, png_path, json_path)
    else:
        with tempfile.TemporaryDirectory(prefix='hgt_') as td:
            work = Path(td)
            zpatch, meta = run_vfp_pipeline(
                args.lat, args.lon, args.half_side_m, args.out_size, work
            )
        write_outputs(zpatch, meta, png_path, json_path)

    hr = max(float(json.loads(json_path.read_text(encoding='utf-8'))['height_range_m']), 1.0)
    side = 2.0 * args.half_side_m
    print(f'OK: {png_path}')
    print(f'     {json_path}')
    print(f'     height_range_m≈{hr:.1f} → en SDF usa <size>{side:.0f} {side:.0f} {hr:.1f}</size>')
    print(
        '     Spawn PX4: z por encima del relieve (p.ej. max elev local + 150 m en sim relativo).'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
