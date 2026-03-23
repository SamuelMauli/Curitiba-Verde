"""Google Earth Engine data collector for Landsat composites."""
import json

import ee

from pipeline.config import (
    AOI_BOUNDS,
    CLOUD_COVER_MAX,
    GEE_COLLECTIONS,
    UNIFIED_BANDS,
    YEARS,
    get_band_mapping,
    get_sensor_for_year,
)


def initialize_gee(service_account_key: str | None = None) -> None:
    """Initialize Earth Engine with service account or default credentials.

    Args:
        service_account_key: Path to service account JSON key file.
                            If None, uses default credentials.
    """
    if service_account_key:
        with open(service_account_key) as f:
            key_data = json.load(f)
        email = key_data.get("client_email", "")
        credentials = ee.ServiceAccountCredentials(email, key_file=service_account_key)
        ee.Initialize(credentials)
    else:
        ee.Initialize()


def get_curitiba_aoi() -> ee.Geometry:
    """Return Curitiba bounding box as EE Geometry."""
    lon_min, lat_min, lon_max, lat_max = AOI_BOUNDS
    return ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])


def get_yearly_composite(year: int) -> ee.Image:
    """Get median composite for Curitiba for a given year.

    Uses dry season (June-September) to minimize clouds.
    Automatically selects the correct sensor for the year.

    Args:
        year: Year to collect (2000-2024).

    Returns:
        ee.Image with unified band names.
    """
    sensor = get_sensor_for_year(year)
    collection_id = GEE_COLLECTIONS[sensor]
    band_mapping = get_band_mapping(sensor)
    aoi = get_curitiba_aoi()

    # Select GEE band names
    gee_bands = [band_mapping[b] for b in UNIFIED_BANDS]

    collection = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(f"{year}-06-01", f"{year}-09-30")
        .filter(ee.Filter.lt("CLOUD_COVER", CLOUD_COVER_MAX))
        .select(gee_bands, UNIFIED_BANDS)  # rename to unified
    )

    composite = collection.median().clip(aoi)
    return composite


def get_qa_band(year: int) -> ee.Image:
    """Get QA_PIXEL band for cloud masking."""
    sensor = get_sensor_for_year(year)
    collection_id = GEE_COLLECTIONS[sensor]
    aoi = get_curitiba_aoi()

    collection = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(f"{year}-06-01", f"{year}-09-30")
        .filter(ee.Filter.lt("CLOUD_COVER", CLOUD_COVER_MAX))
        .select(["QA_PIXEL"])
    )

    return collection.median().clip(aoi)


def get_srtm_dem() -> ee.Image:
    """Get SRTM DEM for Curitiba."""
    aoi = get_curitiba_aoi()
    return ee.Image(GEE_COLLECTIONS["srtm"]).clip(aoi)


def export_to_drive(
    image: ee.Image,
    description: str,
    folder: str = "CwbVerde",
    scale: int = 30,
) -> ee.batch.Task:
    """Export an EE image to Google Drive.

    Args:
        image: ee.Image to export.
        description: Task description and filename.
        folder: Google Drive folder name.
        scale: Pixel size in meters.

    Returns:
        Started export task.
    """
    aoi = get_curitiba_aoi()
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        scale=scale,
        region=aoi,
        maxPixels=1e9,
        fileFormat="GeoTIFF",
    )
    task.start()
    return task


def collect_all_years(
    folder: str = "CwbVerde",
    years: list[int] | None = None,
) -> list[ee.batch.Task]:
    """Export composites for all years to Google Drive.

    Args:
        folder: Google Drive folder.
        years: List of years (default: all from config).

    Returns:
        List of started export tasks.
    """
    if years is None:
        years = YEARS

    tasks = []
    for year in years:
        composite = get_yearly_composite(year)
        task = export_to_drive(
            composite,
            description=f"curitiba_{year}",
            folder=folder,
        )
        tasks.append(task)
        print(f"Started export: curitiba_{year}")

    # Also export SRTM DEM
    dem = get_srtm_dem()
    dem_task = export_to_drive(dem, description="curitiba_srtm", folder=folder)
    tasks.append(dem_task)
    print("Started export: curitiba_srtm")

    return tasks
