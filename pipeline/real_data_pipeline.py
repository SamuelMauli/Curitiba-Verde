"""
CwbVerde — Real Data Pipeline
Downloads REAL satellite imagery from Google Earth Engine,
calculates NDVI, runs classification, and generates change detection maps.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ee
import json
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
import requests
from io import BytesIO
from pipeline.config import DATA_DIR

# Directories
RAW_DIR = DATA_DIR / "raw"
NDVI_DIR = DATA_DIR / "ndvi"
CHANGE_DIR = DATA_DIR / "change"
STATS_DIR = DATA_DIR / "stats"

for d in [RAW_DIR, NDVI_DIR, CHANGE_DIR, STATS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Curitiba bounding box
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = -49.40, -25.65, -49.15, -25.33

# Band mappings for each sensor
LANDSAT5_BANDS = {
    "blue": "SR_B1", "green": "SR_B2", "red": "SR_B3",
    "nir": "SR_B4", "swir1": "SR_B5", "swir2": "SR_B7",
    "qa": "QA_PIXEL",
}
LANDSAT8_BANDS = {
    "blue": "SR_B2", "green": "SR_B3", "red": "SR_B4",
    "nir": "SR_B5", "swir1": "SR_B6", "swir2": "SR_B7",
    "qa": "QA_PIXEL",
}


def get_sensor(year):
    if year <= 2012:
        return "LANDSAT/LT05/C02/T1_L2", LANDSAT5_BANDS, "Landsat 5"
    else:
        return "LANDSAT/LC08/C02/T1_L2", LANDSAT8_BANDS, "Landsat 8"


def init_gee():
    """Initialize Google Earth Engine with service account."""
    key_file = Path(__file__).parent.parent / "gee-service-account.json"
    with open(key_file) as f:
        key = json.load(f)
    credentials = ee.ServiceAccountCredentials(key["client_email"], key_file=str(key_file))
    ee.Initialize(credentials, project=key["project_id"])
    print(f"GEE initialized: {key['client_email']}")


def mask_clouds_landsat(image):
    """Mask clouds using QA_PIXEL band."""
    qa = image.select("QA_PIXEL")
    cloud_mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
    return image.updateMask(cloud_mask)


def get_composite(year, bands):
    """Get cloud-free median composite for a year."""
    collection_id, band_map, sensor_name = get_sensor(year)
    curitiba = ee.Geometry.Rectangle([LON_MIN, LAT_MIN, LON_MAX, LAT_MAX])

    collection = (ee.ImageCollection(collection_id)
                  .filterBounds(curitiba)
                  .filterDate(f"{year}-05-01", f"{year}-10-31")
                  .filter(ee.Filter.lt("CLOUD_COVER", 30))
                  .map(mask_clouds_landsat))

    count = collection.size().getInfo()
    print(f"  {year} ({sensor_name}): {count} cloud-free images")

    if count == 0:
        collection = (ee.ImageCollection(collection_id)
                      .filterBounds(curitiba)
                      .filterDate(f"{year}-01-01", f"{year}-12-31")
                      .filter(ee.Filter.lt("CLOUD_COVER", 50))
                      .map(mask_clouds_landsat))
        count = collection.size().getInfo()
        print(f"    Expanded to full year: {count} images")

    select_bands = [band_map[b] for b in bands]
    rename_bands = list(bands)

    composite = collection.select(select_bands, rename_bands).median().clip(curitiba)
    scaled = composite.multiply(0.0000275).add(-0.2)

    return scaled


def download_single_band(ee_image, band_name, year, scale=30):
    """Download a single band from GEE as GeoTIFF (stays under 50MB limit)."""
    curitiba = ee.Geometry.Rectangle([LON_MIN, LAT_MIN, LON_MAX, LAT_MAX])

    url = ee_image.select([band_name]).getDownloadURL({
        "region": curitiba,
        "scale": scale,
        "format": "GEO_TIFF",
    })

    response = requests.get(url, timeout=300)
    response.raise_for_status()

    with rasterio.open(BytesIO(response.content)) as src:
        arr = src.read(1).astype(np.float32)
        arr[arr < -1] = np.nan
        arr[arr > 2] = np.nan
        profile = src.profile.copy()

    return arr, profile


def download_image_band_by_band(ee_image, bands, year, scale=30):
    """Download an Earth Engine image band by band to avoid size limits."""
    print(f"    Downloading {year} ({len(bands)} bands, one at a time)...")
    arrays = {}
    profile = None
    for band in bands:
        print(f"      Band: {band}...", end=" ", flush=True)
        arr, prof = download_single_band(ee_image, band, year, scale)
        arrays[band] = arr
        if profile is None:
            profile = prof
        print(f"OK ({arr.shape})")

    return arrays, profile


def save_geotiff(data, output_path, nodata=np.nan):
    """Save a 2D numpy array as GeoTIFF with Curitiba bounds."""
    h, w = data.shape
    transform = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, w, h)

    with rasterio.open(
        str(output_path), "w",
        driver="GTiff",
        height=h, width=w,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data.astype(np.float32), 1)

    print(f"    Saved: {output_path.name} ({h}x{w})")


def calculate_ndvi(nir, red):
    """Calculate NDVI from NIR and RED bands."""
    np.seterr(divide="ignore", invalid="ignore")
    ndvi = np.where(
        (nir + red) == 0, np.nan,
        (nir - red) / (nir + red)
    )
    return np.clip(ndvi, -1, 1)


def process_year(year):
    """Download and process satellite data for one year."""
    print(f"\n{'='*50}")
    print(f"Processing {year}")
    print(f"{'='*50}")

    bands = ["blue", "green", "red", "nir", "swir1", "swir2"]

    # Get composite from GEE
    composite = get_composite(year, bands)

    # Download band by band (avoids GEE 50MB size limit)
    arrays, profile = download_image_band_by_band(composite, bands, year)

    nir = arrays["nir"]
    red = arrays["red"]

    # Calculate NDVI
    ndvi = calculate_ndvi(nir, red)
    ndvi_path = NDVI_DIR / f"ndvi_{year}.tif"
    save_geotiff(ndvi, ndvi_path)

    # Save raw composite
    raw_path = RAW_DIR / f"composite_{year}.tif"
    h, w = nir.shape
    transform = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, w, h)
    with rasterio.open(
        str(raw_path), "w",
        driver="GTiff", height=h, width=w,
        count=len(bands), dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
    ) as dst:
        for i, band_name in enumerate(bands):
            dst.write(arrays[band_name], i + 1)
    print(f"    Saved composite: {raw_path.name} ({len(bands)} bands)")

    # Compute stats
    valid_ndvi = ndvi[~np.isnan(ndvi)]
    stats = {
        "year": year,
        "ndvi_mean": float(np.nanmean(ndvi)),
        "ndvi_std": float(np.nanstd(ndvi)),
        "ndvi_min": float(np.nanmin(ndvi)),
        "ndvi_max": float(np.nanmax(ndvi)),
        "green_pixels": int((valid_ndvi > 0.3).sum()),
        "total_pixels": int(len(valid_ndvi)),
        "green_area_ha": float((valid_ndvi > 0.3).sum() * 0.09),
        "green_percent": float((valid_ndvi > 0.3).sum() / max(len(valid_ndvi), 1) * 100),
        "water_pixels": int((valid_ndvi < -0.1).sum()),
        "urban_pixels": int(((valid_ndvi >= 0.0) & (valid_ndvi < 0.2)).sum()),
        "width": w,
        "height": h,
    }

    print(f"    NDVI mean: {stats['ndvi_mean']:.4f}")
    print(f"    Green cover: {stats['green_percent']:.1f}%")
    print(f"    Dimensions: {w}x{h} pixels")

    return stats


def compute_change_detection(years_processed):
    """Compute change detection between consecutive years."""
    print(f"\n{'='*50}")
    print("Computing Change Detection")
    print(f"{'='*50}")

    sorted_years = sorted(years_processed)

    for i in range(1, len(sorted_years)):
        year_a = sorted_years[i - 1]
        year_b = sorted_years[i]

        path_a = NDVI_DIR / f"ndvi_{year_a}.tif"
        path_b = NDVI_DIR / f"ndvi_{year_b}.tif"

        if not path_a.exists() or not path_b.exists():
            continue

        with rasterio.open(str(path_a)) as src:
            ndvi_a = src.read(1)
        with rasterio.open(str(path_b)) as src:
            ndvi_b = src.read(1)

        min_h = min(ndvi_a.shape[0], ndvi_b.shape[0])
        min_w = min(ndvi_a.shape[1], ndvi_b.shape[1])
        ndvi_a = ndvi_a[:min_h, :min_w]
        ndvi_b = ndvi_b[:min_h, :min_w]

        change = ndvi_b - ndvi_a
        change[np.isnan(change)] = 0

        change_classified = np.zeros_like(change, dtype=np.float32)
        change_classified[change < -0.1] = -1
        change_classified[change > 0.1] = 1

        output_path = CHANGE_DIR / f"change_{year_a}_{year_b}.tif"
        save_geotiff(change_classified, output_path, nodata=0)

        loss = (change_classified == -1).sum() * 0.09
        gain = (change_classified == 1).sum() * 0.09
        print(f"  {year_a} -> {year_b}: Loss={loss:.1f}ha, Gain={gain:.1f}ha")


def save_statistics(all_stats):
    """Save yearly statistics as Parquet."""
    import pandas as pd

    df = pd.DataFrame(all_stats)
    parquet_path = STATS_DIR / "yearly_summary.parquet"
    df.to_parquet(str(parquet_path), index=False)
    print(f"\nStatistics saved: {parquet_path}")
    print(df[["year", "ndvi_mean", "green_percent", "green_area_ha"]].to_string(index=False))


def main():
    """Run the complete real data pipeline."""
    print("=" * 60)
    print("CwbVerde - REAL DATA PIPELINE")
    print("Downloading actual satellite imagery from Google Earth Engine")
    print("=" * 60)

    init_gee()

    target_years = [2000, 2005, 2010, 2013, 2015, 2018, 2020, 2023]

    all_stats = []
    for year in target_years:
        try:
            stats = process_year(year)
            all_stats.append(stats)
        except Exception as e:
            print(f"  ERROR processing {year}: {e}")
            import traceback
            traceback.print_exc()

    if len(all_stats) >= 2:
        years_done = [s["year"] for s in all_stats]
        compute_change_detection(years_done)

    if all_stats:
        save_statistics(all_stats)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print(f"Processed {len(all_stats)} years of REAL satellite data")
    print("=" * 60)


if __name__ == "__main__":
    main()
