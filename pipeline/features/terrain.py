# pipeline/features/terrain.py
"""Terrain features — elevation and slope from SRTM DEM."""
import numpy as np
import rasterio


def compute_slope(elevation: np.ndarray, pixel_size: float = 30.0) -> np.ndarray:
    """Compute slope in degrees from a DEM array.

    Uses numpy gradient to compute dz/dx and dz/dy, then converts to degrees.

    Args:
        elevation: 2D array of elevation values (meters).
        pixel_size: Ground distance per pixel (meters).

    Returns:
        2D array of slope in degrees.
    """
    dy, dx = np.gradient(elevation, pixel_size)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    return slope_deg.astype(np.float32)


def load_terrain_features(
    dem_path: str, pixel_size: float = 30.0
) -> dict[str, np.ndarray]:
    """Load DEM and compute elevation + slope.

    Args:
        dem_path: Path to DEM GeoTIFF (e.g., SRTM).
        pixel_size: Ground distance per pixel (meters).

    Returns:
        Dict with "elevation" and "slope" arrays.
    """
    with rasterio.open(dem_path) as src:
        elevation = src.read(1).astype(np.float32)

    slope = compute_slope(elevation, pixel_size)
    return {"elevation": elevation, "slope": slope}
