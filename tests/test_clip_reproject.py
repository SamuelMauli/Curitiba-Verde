# tests/test_clip_reproject.py
import numpy as np
import pytest
import rasterio
from shapely.geometry import box, mapping
from pipeline.preprocess.clip_reproject import clip_to_aoi, reproject_raster


class TestClipToAoi:
    def test_output_smaller_than_input(self, synthetic_raster_path, small_aoi_geometry, tmp_path):
        """Clipped raster should be smaller than original."""
        output = tmp_path / "clipped.tif"
        clip_to_aoi(str(synthetic_raster_path), small_aoi_geometry, str(output))

        with rasterio.open(synthetic_raster_path) as src_orig:
            orig_pixels = src_orig.width * src_orig.height
        with rasterio.open(output) as src_clip:
            clip_pixels = src_clip.width * src_clip.height

        assert clip_pixels < orig_pixels

    def test_output_has_same_band_count(self, synthetic_raster_path, small_aoi_geometry, tmp_path):
        """Clipped raster preserves band count."""
        output = tmp_path / "clipped.tif"
        clip_to_aoi(str(synthetic_raster_path), small_aoi_geometry, str(output))

        with rasterio.open(output) as src:
            assert src.count == 6

    def test_output_exists(self, synthetic_raster_path, small_aoi_geometry, tmp_path):
        """Output file is created."""
        output = tmp_path / "clipped.tif"
        clip_to_aoi(str(synthetic_raster_path), small_aoi_geometry, str(output))
        assert output.exists()


class TestReprojectRaster:
    def test_output_crs_matches_target(self, synthetic_raster_path, tmp_path):
        """Reprojected raster has the target CRS."""
        output = tmp_path / "reprojected.tif"
        reproject_raster(
            str(synthetic_raster_path), str(output), dst_crs="EPSG:31982"
        )
        with rasterio.open(output) as src:
            assert src.crs.to_epsg() == 31982

    def test_data_preserved(self, synthetic_raster_path, tmp_path):
        """Reprojected raster has non-zero data."""
        output = tmp_path / "reprojected.tif"
        reproject_raster(
            str(synthetic_raster_path), str(output), dst_crs="EPSG:31982"
        )
        with rasterio.open(output) as src:
            data = src.read(1)
            assert data.max() > 0
