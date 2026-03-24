"""
CwbVerde — Land Use Classification using Multiple Spectral Indices
Uses NDVI + NDWI + NDBI + MNDWI from real Landsat bands to properly classify:
- Water (lakes, rivers like Barigui)
- Dense vegetation (forests, parks)
- Light vegetation (grass, gardens)
- Urban (buildings, asphalt, concrete)
- Bare soil (construction sites, exposed earth)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from pipeline.config import DATA_DIR

RAW_DIR = DATA_DIR / "raw"
NDVI_DIR = DATA_DIR / "ndvi"
CLASS_DIR = DATA_DIR / "classification"
CLASS_DIR.mkdir(parents=True, exist_ok=True)

LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = -49.40, -25.65, -49.15, -25.33


def classify_year(year):
    """
    Classify land use for a given year using multiple spectral indices.

    Band order in composite: blue(0), green(1), red(2), nir(3), swir1(4), swir2(5)

    Classification rules (decision tree, order matters):
    1. MNDWI > 0.0 AND NDVI < 0.1 → WATER (catches lakes, rivers)
    2. NDWI > 0.0 AND NDVI < 0.15 → WATER (backup water detection)
    3. NDVI > 0.5 → DENSE VEGETATION (forests, dense parks)
    4. NDVI > 0.3 AND NDBI < 0.0 → LIGHT VEGETATION (grass, gardens)
    5. NDBI > 0.0 AND NDVI < 0.25 → URBAN (buildings, asphalt)
    6. NDVI < 0.15 AND NDBI > -0.1 → BARE SOIL (exposed earth)
    7. Remaining → LIGHT VEGETATION (default for mixed pixels)
    """
    composite_path = RAW_DIR / f"composite_{year}.tif"
    if not composite_path.exists():
        print(f"  No composite for {year}, skipping")
        return None

    print(f"  Classifying {year}...")

    with rasterio.open(str(composite_path)) as src:
        blue = src.read(1).astype(np.float64)
        green = src.read(2).astype(np.float64)
        red = src.read(3).astype(np.float64)
        nir = src.read(4).astype(np.float64)
        swir1 = src.read(5).astype(np.float64)
        swir2 = src.read(6).astype(np.float64)

    np.seterr(divide="ignore", invalid="ignore")

    # Calculate indices
    ndvi = np.where((nir + red) != 0, (nir - red) / (nir + red), 0)
    ndwi = np.where((green + nir) != 0, (green - nir) / (green + nir), 0)
    ndbi = np.where((swir1 + nir) != 0, (swir1 - nir) / (swir1 + nir), 0)
    mndwi = np.where((green + swir1) != 0, (green - swir1) / (green + swir1), 0)

    # Classification: 0=nodata, 1=water, 2=dense_veg, 3=light_veg, 4=urban, 5=bare_soil
    h, w = ndvi.shape
    classification = np.zeros((h, w), dtype=np.uint8)

    # Detect nodata (all bands are NaN or 0)
    nodata_mask = np.isnan(nir) | np.isnan(red) | ((nir == 0) & (red == 0) & (green == 0))

    # 1. WATER — MNDWI > 0 and low NDVI (catches lakes like Barigui)
    water_mask = ((mndwi > 0.0) & (ndvi < 0.1)) | ((ndwi > 0.0) & (ndvi < 0.15))
    classification[water_mask] = 1

    # 2. DENSE VEGETATION — high NDVI (forests, Parque Barigui forest areas)
    dense_veg_mask = (ndvi > 0.5) & (~water_mask)
    classification[dense_veg_mask] = 2

    # 3. LIGHT VEGETATION — moderate NDVI, low NDBI (grass, gardens, parks)
    light_veg_mask = (ndvi > 0.3) & (ndbi < 0.0) & (~water_mask) & (~dense_veg_mask)
    classification[light_veg_mask] = 3

    # 4. URBAN — high NDBI, low NDVI (buildings, concrete, asphalt)
    urban_mask = (ndbi > 0.0) & (ndvi < 0.25) & (~water_mask) & (~dense_veg_mask) & (~light_veg_mask)
    classification[urban_mask] = 4

    # 5. BARE SOIL — very low NDVI, moderate NDBI
    bare_soil_mask = (ndvi < 0.15) & (ndbi > -0.1) & (~water_mask) & (~urban_mask) & (~dense_veg_mask) & (~light_veg_mask)
    classification[bare_soil_mask] = 5

    # 6. Default remaining pixels to light vegetation
    remaining = (classification == 0) & (~nodata_mask)
    classification[remaining] = 3

    # Set nodata
    classification[nodata_mask] = 0

    # Save classification raster
    output_path = CLASS_DIR / f"classification_{year}.tif"
    transform = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, w, h)
    with rasterio.open(
        str(output_path), "w",
        driver="GTiff", height=h, width=w,
        count=1, dtype="uint8",
        crs=CRS.from_epsg(4326),
        transform=transform, nodata=0,
    ) as dst:
        dst.write(classification, 1)

    # Stats
    valid = classification[classification > 0]
    total = len(valid)
    stats = {
        "year": year,
        "water_pct": float((valid == 1).sum() / total * 100) if total > 0 else 0,
        "dense_veg_pct": float((valid == 2).sum() / total * 100) if total > 0 else 0,
        "light_veg_pct": float((valid == 3).sum() / total * 100) if total > 0 else 0,
        "urban_pct": float((valid == 4).sum() / total * 100) if total > 0 else 0,
        "bare_soil_pct": float((valid == 5).sum() / total * 100) if total > 0 else 0,
        "water_ha": float((valid == 1).sum() * 0.09),
        "dense_veg_ha": float((valid == 2).sum() * 0.09),
        "light_veg_ha": float((valid == 3).sum() * 0.09),
        "urban_ha": float((valid == 4).sum() * 0.09),
        "bare_soil_ha": float((valid == 5).sum() * 0.09),
    }

    print(f"    Water:      {stats['water_pct']:5.1f}% ({stats['water_ha']:.0f} ha)")
    print(f"    Dense veg:  {stats['dense_veg_pct']:5.1f}% ({stats['dense_veg_ha']:.0f} ha)")
    print(f"    Light veg:  {stats['light_veg_pct']:5.1f}% ({stats['light_veg_ha']:.0f} ha)")
    print(f"    Urban:      {stats['urban_pct']:5.1f}% ({stats['urban_ha']:.0f} ha)")
    print(f"    Bare soil:  {stats['bare_soil_pct']:5.1f}% ({stats['bare_soil_ha']:.0f} ha)")

    return stats


def main():
    """Classify all years."""
    import pandas as pd

    print("=" * 60)
    print("CwbVerde — Land Use Classification")
    print("Using NDVI + NDWI + NDBI + MNDWI")
    print("=" * 60)

    all_stats = []
    composites = sorted(RAW_DIR.glob("composite_*.tif"))
    print(f"Found {len(composites)} composites to classify\n")

    for f in composites:
        year = int(f.stem.split("_")[1])
        stats = classify_year(year)
        if stats:
            all_stats.append(stats)
        print()

    if all_stats:
        df = pd.DataFrame(all_stats).sort_values("year")
        output = DATA_DIR / "stats" / "classification_summary.parquet"
        df.to_parquet(str(output), index=False)
        print(f"\nClassification stats saved: {output}")
        print(df[["year", "water_pct", "dense_veg_pct", "light_veg_pct", "urban_pct", "bare_soil_pct"]].to_string(index=False))

    print(f"\nClassified {len(all_stats)} years")


if __name__ == "__main__":
    main()
