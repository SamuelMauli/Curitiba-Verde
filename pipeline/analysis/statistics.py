"""Zonal statistics and yearly summaries."""
import numpy as np
import geopandas as gpd
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from pipeline.config import PIXEL_AREA_HA, CLASS_NAMES


def compute_zonal_stats(
    ndvi: np.ndarray,
    bairros: gpd.GeoDataFrame,
    transform: Affine,
    crs: str,
) -> list[dict]:
    """Compute NDVI statistics per bairro.

    Args:
        ndvi: 2D NDVI array.
        bairros: GeoDataFrame with bairro geometries and 'nome' column.
        transform: Rasterio transform of the NDVI raster.
        crs: CRS of the NDVI raster.

    Returns:
        List of dicts, one per bairro, with stats.
    """
    bairros_proj = bairros.to_crs(crs)
    results = []

    for _, row in bairros_proj.iterrows():
        mask = geometry_mask(
            [row.geometry],
            out_shape=ndvi.shape,
            transform=transform,
            invert=True,
        )
        pixels = ndvi[mask]
        valid = pixels[~np.isnan(pixels)]

        if len(valid) == 0:
            results.append({
                "nome": row.get("nome", "Unknown"),
                "ndvi_mean": 0.0,
                "ndvi_std": 0.0,
                "green_area_ha": 0.0,
                "total_pixels": 0,
            })
            continue

        green_pixels = (valid > 0.3).sum()
        results.append({
            "nome": row.get("nome", "Unknown"),
            "ndvi_mean": float(valid.mean()),
            "ndvi_std": float(valid.std()),
            "green_area_ha": float(green_pixels * PIXEL_AREA_HA),
            "total_pixels": int(len(valid)),
        })

    return results


def compute_yearly_summary(
    ndvi: np.ndarray,
    classification: np.ndarray,
    year: int,
) -> dict:
    """Compute summary statistics for a single year.

    Args:
        ndvi: 2D NDVI array.
        classification: 2D classification array (1-5).
        year: Year label.

    Returns:
        Dict with year, ndvi stats, green area, class distribution.
    """
    valid_ndvi = ndvi[~np.isnan(ndvi)]
    total_pixels = (classification > 0).sum()
    green_pixels = ((classification == 1) | (classification == 2)).sum()

    class_dist = {}
    for cls_id, cls_name in CLASS_NAMES.items():
        count = int((classification == cls_id).sum())
        class_dist[cls_name] = {
            "pixels": count,
            "hectares": float(count * PIXEL_AREA_HA),
            "percent": float(count / total_pixels * 100) if total_pixels > 0 else 0,
        }

    return {
        "year": year,
        "ndvi_mean": float(valid_ndvi.mean()) if len(valid_ndvi) > 0 else 0,
        "ndvi_std": float(valid_ndvi.std()) if len(valid_ndvi) > 0 else 0,
        "green_area_ha": float(green_pixels * PIXEL_AREA_HA),
        "total_area_ha": float(total_pixels * PIXEL_AREA_HA),
        "green_percent": float(green_pixels / total_pixels * 100) if total_pixels > 0 else 0,
        "class_distribution": class_dist,
    }
