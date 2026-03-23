"""Clip rasters to AOI and reproject to target CRS."""
import rasterio
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import mapping


def clip_to_aoi(
    input_path: str,
    aoi_geometry,
    output_path: str,
    nodata: float = 0.0,
) -> None:
    """Clip a raster to an area of interest geometry.

    Args:
        input_path: Path to input GeoTIFF.
        aoi_geometry: Shapely geometry to clip to.
        output_path: Path for clipped output.
        nodata: Nodata value for pixels outside AOI.
    """
    shapes = [mapping(aoi_geometry)]

    with rasterio.open(input_path) as src:
        out_image, out_transform = rasterio_mask(
            src, shapes, crop=True, nodata=nodata
        )
        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata": nodata,
        })

    with rasterio.open(output_path, "w", **out_meta) as dst:
        dst.write(out_image)


def reproject_raster(
    input_path: str,
    output_path: str,
    dst_crs: str = "EPSG:31982",
    resampling: Resampling = Resampling.bilinear,
) -> None:
    """Reproject a raster to a target CRS.

    Args:
        input_path: Path to input GeoTIFF.
        output_path: Path for reprojected output.
        dst_crs: Target CRS (default: SIRGAS 2000 UTM 22S).
        resampling: Resampling method.
    """
    with rasterio.open(input_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        meta = src.meta.copy()
        meta.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height,
        })

        with rasterio.open(output_path, "w", **meta) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                )
