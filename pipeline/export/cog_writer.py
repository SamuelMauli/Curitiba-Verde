"""Write Cloud-Optimized GeoTIFFs (COGs)."""
import numpy as np
import rasterio
from rasterio.transform import Affine


def write_cog(
    data: np.ndarray,
    output_path: str,
    crs: str,
    transform: Affine,
    nodata: float | None = None,
    overview_levels: list[int] | None = None,
) -> None:
    """Write a numpy array as a Cloud-Optimized GeoTIFF.

    Args:
        data: 3D array (bands, height, width) or 2D (height, width).
        output_path: Path for output COG.
        crs: Coordinate reference system string.
        transform: Rasterio affine transform.
        nodata: Nodata value (optional).
        overview_levels: Overview decimation levels (default: auto).
    """
    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    bands, height, width = data.shape

    if overview_levels is None:
        # Auto-compute overview levels based on raster size
        max_dim = max(height, width)
        overview_levels = []
        level = 2
        while max_dim / level >= 64:
            overview_levels.append(level)
            level *= 2

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": bands,
        "dtype": data.dtype,
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    if nodata is not None:
        profile["nodata"] = nodata

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data)
        if overview_levels:
            dst.build_overviews(overview_levels, rasterio.enums.Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")
