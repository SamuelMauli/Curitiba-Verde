import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from pipeline.export.cog_writer import write_cog


class TestWriteCOG:
    def test_output_is_valid_geotiff(self, tmp_path):
        """Written COG is a valid GeoTIFF."""
        data = np.random.uniform(0, 1, (1, 100, 100)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 100, 100)
        output = tmp_path / "test.tif"

        write_cog(
            data, str(output),
            crs="EPSG:31982", transform=transform,
        )

        with rasterio.open(output) as src:
            assert src.count == 1
            assert src.crs.to_string() == "EPSG:31982"
            read_data = src.read(1)
            assert read_data.shape == (100, 100)

    def test_multiband_cog(self, tmp_path):
        """COG with multiple bands."""
        data = np.random.uniform(0, 1, (3, 50, 50)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 50, 50)
        output = tmp_path / "multi.tif"

        write_cog(data, str(output), crs="EPSG:31982", transform=transform)

        with rasterio.open(output) as src:
            assert src.count == 3

    def test_cog_has_overviews(self, tmp_path):
        """COG includes internal overviews for fast rendering."""
        data = np.random.uniform(0, 1, (1, 512, 512)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 512, 512)
        output = tmp_path / "overview.tif"

        write_cog(data, str(output), crs="EPSG:31982", transform=transform)

        with rasterio.open(output) as src:
            assert len(src.overviews(1)) > 0

    def test_cog_uses_deflate_compression(self, tmp_path):
        """COG uses deflate compression."""
        data = np.random.uniform(0, 1, (1, 100, 100)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 100, 100)
        output = tmp_path / "compressed.tif"

        write_cog(data, str(output), crs="EPSG:31982", transform=transform)

        with rasterio.open(output) as src:
            assert src.compression == rasterio.enums.Compression.deflate
