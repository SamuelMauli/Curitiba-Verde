import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
"""Map rendering utilities — PNG overlays for Folium."""
import base64
from io import BytesIO
import numpy as np
from pathlib import Path
from app.config import DATA_DIR
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Bounding box used for ALL rasters
_LON_MIN, _LAT_MIN, _LON_MAX, _LAT_MAX = -49.40, -25.65, -49.15, -25.33

# Cached city mask (computed once per shape)
_curitiba_mask_cache: dict = {}


def _get_city_mask(h: int, w: int) -> np.ndarray:
    """
    Return a boolean mask of shape (h, w) that is True inside Curitiba.
    Pixels outside the city boundary will have alpha=0.
    Cached after first call.
    """
    import json, rasterio.features, rasterio.transform
    key = (h, w)
    if key in _curitiba_mask_cache:
        return _curitiba_mask_cache[key]

    boundary_path = DATA_DIR / "shapefiles" / "curitiba_boundary.geojson"
    if not boundary_path.exists():
        # No boundary file — keep everything visible
        mask = np.ones((h, w), dtype=bool)
        _curitiba_mask_cache[key] = mask
        return mask

    with open(boundary_path) as f:
        gj = json.load(f)

    # Collect all geometries
    geometries = [feat["geometry"] for feat in gj.get("features", [])]
    if not geometries:
        mask = np.ones((h, w), dtype=bool)
        _curitiba_mask_cache[key] = mask
        return mask

    transform = rasterio.transform.from_bounds(
        _LON_MIN, _LAT_MIN, _LON_MAX, _LAT_MAX, w, h
    )
    # geometry_mask returns True OUTSIDE — invert to get True INSIDE
    outside = rasterio.features.geometry_mask(
        geometries, transform=transform, invert=False, out_shape=(h, w)
    )
    mask = ~outside
    _curitiba_mask_cache[key] = mask
    return mask


# Class colormap (matches app/config.py CLASS_COLORS)
# 0=nodata (transparent), 1=water, 2=dense_veg, 3=light_veg, 4=urban, 5=bare_soil
_CLASS_RGBA = {
    0: (0,   0,   0,   0),    # transparent
    1: (33,  150, 243, 210),  # blue — water
    2: (27,  94,  32,  220),  # dark green — dense veg
    3: (102, 187, 106, 200),  # light green — light veg
    4: (244, 67,  54,  200),  # red — urban
    5: (255, 152, 0,   200),  # orange — bare soil
}


def _to_png_b64(img_rgba: np.ndarray, upsample: int = 1,
                resample=None) -> str:
    """Convert RGBA uint8 array (H×W×4) to base64 PNG string.

    upsample: integer scale factor (e.g. 3 → 3× larger image, sharper on zoom)
    resample: PIL resampling filter (NEAREST for classification, LANCZOS for photo)
    """
    from PIL import Image
    img = Image.fromarray(img_rgba, mode="RGBA")
    if upsample > 1:
        new_w = img.width * upsample
        new_h = img.height * upsample
        img = img.resize((new_w, new_h), resample=resample or Image.NEAREST)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


def render_classification_png_b64(year: int) -> str:
    """
    Render classification raster as a transparent RGBA PNG.
    Each class gets its own color (see _CLASS_RGBA above).
    """
    import rasterio
    path = DATA_DIR / "classification" / f"classification_{year}.tif"
    if not path.exists():
        return ""
    try:
        with rasterio.open(str(path)) as src:
            data = src.read(1)  # uint8, values 0-5
        h, w = data.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        for class_id, color_rgba in _CLASS_RGBA.items():
            mask = data == class_id
            rgba[mask] = color_rgba
        # Mask pixels outside Curitiba boundary → transparent
        city_mask = _get_city_mask(h, w)
        rgba[~city_mask, 3] = 0
        from PIL import Image
        return _to_png_b64(rgba, upsample=3, resample=Image.NEAREST)
    except Exception as e:
        print(f"render_classification_png_b64 error: {e}")
        return ""


def render_satellite_rgb_png_b64(year: int, percentile_low: float = 2.0,
                                  percentile_high: float = 98.0) -> str:
    """
    Render true-color satellite composite (bands red/green/blue) as PNG.
    Applies percentile stretch per band so the image is visible (raw SR values
    are low; stretching to 2nd-98th percentile gives a natural-looking image).
    """
    import rasterio
    path = DATA_DIR / "raw" / f"composite_{year}.tif"
    if not path.exists():
        return ""
    try:
        with rasterio.open(str(path)) as src:
            red   = src.read(3).astype(np.float32)  # band 3
            green = src.read(2).astype(np.float32)  # band 2
            blue  = src.read(1).astype(np.float32)  # band 1

        def stretch(band: np.ndarray) -> np.ndarray:
            """Percentile stretch → uint8."""
            valid = band[np.isfinite(band) & (band > -0.5)]
            if len(valid) < 100:
                return np.zeros_like(band, dtype=np.uint8)
            p_lo = np.percentile(valid, percentile_low)
            p_hi = np.percentile(valid, percentile_high)
            if p_hi <= p_lo:
                return np.zeros_like(band, dtype=np.uint8)
            stretched = (band - p_lo) / (p_hi - p_lo)
            return np.clip(stretched * 255, 0, 255).astype(np.uint8)

        r = stretch(red)
        g = stretch(green)
        b = stretch(blue)

        h, w = r.shape
        # Build RGBA: full opacity where data exists, transparent where nodata
        nodata_mask = (red < -0.5) | ~np.isfinite(red)
        alpha = np.where(nodata_mask, 0, 255).astype(np.uint8)

        rgba = np.stack([r, g, b, alpha], axis=-1)
        # Mask pixels outside Curitiba boundary → transparent
        city_mask = _get_city_mask(h, w)
        rgba[~city_mask, 3] = 0
        from PIL import Image
        return _to_png_b64(rgba, upsample=3, resample=Image.LANCZOS)
    except Exception as e:
        print(f"render_satellite_rgb_png_b64 error: {e}")
        return ""


def render_ndvi_png_b64(year: int) -> str:
    """Render NDVI raster as base64 PNG with RdYlGn colormap."""
    import rasterio
    cog_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    if not cog_path.exists():
        return ""
    try:
        with rasterio.open(str(cog_path)) as src:
            ndvi = src.read(1).astype(np.float32)

        ndvi[ndvi < -1]  = np.nan
        ndvi[ndvi > 1]   = np.nan
        nodata_mask = ~np.isfinite(ndvi)

        # Normalize -0.2..0.8 → 0..1 for colormap
        vmin, vmax = -0.2, 0.8
        normalized = np.clip((ndvi - vmin) / (vmax - vmin), 0, 1)

        cmap = plt.get_cmap("RdYlGn")
        rgba_f = cmap(normalized)                         # float (H, W, 4)
        rgba = (rgba_f * 255).astype(np.uint8)
        rgba[nodata_mask, 3] = 0                          # transparent nodata
        # Mask pixels outside Curitiba boundary → transparent
        city_mask = _get_city_mask(ndvi.shape[0], ndvi.shape[1])
        rgba[~city_mask, 3] = 0
        from PIL import Image
        return _to_png_b64(rgba, upsample=3, resample=Image.BILINEAR)
    except Exception as e:
        print(f"render_ndvi_png_b64 error: {e}")
        return ""


def get_ndvi_stats_for_area(year: int, bounds: tuple = None) -> dict:
    """Get NDVI statistics for a given year."""
    import rasterio
    cog_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    if not cog_path.exists():
        return {}
    with rasterio.open(str(cog_path)) as src:
        ndvi = src.read(1)
    valid = ndvi[(ndvi > -1) & (ndvi < 1) & np.isfinite(ndvi)]
    if len(valid) == 0:
        return {}
    return {
        "ndvi_mean":    float(valid.mean()),
        "ndvi_std":     float(valid.std()),
        "green_pixels": int((valid > 0.3).sum()),
        "total_pixels": int(len(valid)),
        "green_area_ha": float((valid > 0.3).sum() * 0.09),
    }
