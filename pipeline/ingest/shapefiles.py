"""Load Curitiba boundary and bairros shapefiles."""
import geopandas as gpd
from shapely.geometry import box

from pipeline.config import AOI_BOUNDS, TARGET_CRS


def load_curitiba_boundary(shapefile_path: str | None = None) -> gpd.GeoDataFrame:
    """Load Curitiba municipal boundary.

    If no shapefile is provided, creates a bounding box from config.

    Args:
        shapefile_path: Path to Curitiba boundary shapefile.

    Returns:
        GeoDataFrame with Curitiba geometry in EPSG:4326.
    """
    if shapefile_path:
        gdf = gpd.read_file(shapefile_path)
        return gdf.to_crs("EPSG:4326")

    # Fallback: use bounding box from config
    geometry = box(*AOI_BOUNDS)
    return gpd.GeoDataFrame(
        {"name": ["Curitiba"]},
        geometry=[geometry],
        crs="EPSG:4326",
    )


def load_bairros(shapefile_path: str) -> gpd.GeoDataFrame:
    """Load Curitiba bairros (neighborhoods) shapefile.

    Args:
        shapefile_path: Path to bairros shapefile.

    Returns:
        GeoDataFrame with bairro geometries, reprojected to EPSG:4326.
    """
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs("EPSG:4326")
    return gdf


def get_aoi_geometry():
    """Return Curitiba AOI as shapely geometry."""
    return box(*AOI_BOUNDS)
