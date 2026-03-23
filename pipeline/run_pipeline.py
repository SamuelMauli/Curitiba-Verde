"""Pipeline orchestrator — runs all stages in sequence."""
import logging
from pathlib import Path

from pipeline.config import (
    DATA_DIR,
    OUTPUT_DIR,
    PIXEL_SIZE_M,
    YEARS,
    get_sensor_for_year,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_preprocess(year: int) -> Path:
    """Run preprocessing for a single year: harmonize + clip + reproject.

    Expects raw GeoTIFF at data/raw/curitiba_{year}.tif
    Outputs to data/processed/curitiba_{year}.tif
    """
    from pipeline.ingest.shapefiles import get_aoi_geometry
    from pipeline.preprocess.clip_reproject import clip_to_aoi, reproject_raster
    from pipeline.preprocess.harmonize import harmonize_bands

    raw_path = DATA_DIR / "raw" / f"curitiba_{year}.tif"
    harmonized_path = DATA_DIR / "processed" / f"harmonized_{year}.tif"
    clipped_path = DATA_DIR / "processed" / f"clipped_{year}.tif"
    output_path = DATA_DIR / "processed" / f"curitiba_{year}.tif"

    if not raw_path.exists():
        logger.warning(f"Raw file not found: {raw_path}, skipping year {year}")
        return output_path

    # Step 1: Harmonize (DN → reflectance)
    sensor = get_sensor_for_year(year)
    logger.info(f"[{year}] Harmonizing bands ({sensor})...")
    harmonized_path.parent.mkdir(parents=True, exist_ok=True)
    harmonize_bands(str(raw_path), str(harmonized_path), sensor=sensor)

    # Step 2: Clip to Curitiba AOI
    aoi = get_aoi_geometry()
    logger.info(f"[{year}] Clipping to Curitiba AOI...")
    clip_to_aoi(str(harmonized_path), aoi, str(clipped_path))

    # Step 3: Reproject to SIRGAS 2000
    logger.info(f"[{year}] Reprojecting to EPSG:31982...")
    reproject_raster(str(clipped_path), str(output_path))

    # Cleanup intermediates
    harmonized_path.unlink(missing_ok=True)
    clipped_path.unlink(missing_ok=True)

    logger.info(f"[{year}] Preprocessing complete → {output_path}")
    return output_path


def run_features(year: int) -> Path:
    """Compute spectral indices for a single year.

    Reads data/processed/curitiba_{year}.tif
    Outputs NDVI to data/ndvi/ndvi_{year}.tif
    Outputs feature stack to data/features/features_{year}.tif
    """
    import numpy as np
    import rasterio

    from pipeline.export.cog_writer import write_cog
    from pipeline.features.indices import compute_all_indices

    input_path = DATA_DIR / "processed" / f"curitiba_{year}.tif"
    ndvi_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    features_path = DATA_DIR / "features" / f"features_{year}.tif"

    if not input_path.exists():
        logger.warning(f"Processed file not found: {input_path}, skipping")
        return features_path

    with rasterio.open(input_path) as src:
        bands = {
            "blue": src.read(1),
            "green": src.read(2),
            "red": src.read(3),
            "nir": src.read(4),
            "swir1": src.read(5),
            "swir2": src.read(6),
        }
        transform = src.transform
        crs = src.crs.to_string()

    # Compute indices
    logger.info(f"[{year}] Computing spectral indices...")
    indices = compute_all_indices(bands)

    # Save NDVI separately
    ndvi_path.parent.mkdir(parents=True, exist_ok=True)
    write_cog(indices["ndvi"], str(ndvi_path), crs=crs, transform=transform)
    logger.info(f"[{year}] NDVI saved → {ndvi_path}")

    # Stack all features: 6 bands + 5 indices = 11
    # (Texture and terrain added separately in full pipeline)
    feature_arrays = [
        bands["blue"], bands["green"], bands["red"],
        bands["nir"], bands["swir1"], bands["swir2"],
        indices["ndvi"], indices["ndwi"], indices["ndbi"],
        indices["savi"], indices["evi"],
    ]
    stack = np.stack(feature_arrays, axis=0).astype(np.float32)

    features_path.parent.mkdir(parents=True, exist_ok=True)
    write_cog(stack, str(features_path), crs=crs, transform=transform)
    logger.info(f"[{year}] Feature stack (11 bands) saved → {features_path}")

    return features_path


def run_pipeline(
    years: list[int] | None = None,
    steps: list[str] | None = None,
) -> None:
    """Run the full pipeline for all years.

    Args:
        years: List of years to process (default: all).
        steps: List of steps to run: ["preprocess", "features"].
               Default: all steps.
    """
    if years is None:
        years = YEARS
    if steps is None:
        steps = ["preprocess", "features"]

    logger.info(f"Starting pipeline for {len(years)} years: {years[0]}-{years[-1]}")

    for year in years:
        if "preprocess" in steps:
            run_preprocess(year)
        if "features" in steps:
            run_features(year)

    logger.info("Pipeline complete!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CwbVerde Pipeline")
    parser.add_argument("--years", nargs="+", type=int, default=None)
    parser.add_argument("--steps", nargs="+", default=None)
    args = parser.parse_args()
    run_pipeline(years=args.years, steps=args.steps)
