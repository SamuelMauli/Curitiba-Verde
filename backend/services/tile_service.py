"""Tile service — serves map tiles from COG rasters."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import rasterio
from io import BytesIO
from pipeline.config import DATA_DIR
from PIL import Image


class TileService:
    def __init__(self):
        self.ndvi_dir = DATA_DIR / "ndvi"
        self.change_dir = DATA_DIR / "change"
        self.class_dir = DATA_DIR / "classification"

    def get_available_years(self) -> list[int]:
        years = []
        for f in sorted(self.ndvi_dir.glob("ndvi_*.tif")):
            try:
                years.append(int(f.stem.split("_")[1]))
            except (IndexError, ValueError):
                pass
        return years

    # Class definitions: name -> (condition_func, RGBA color)
    CLASS_COLORS = {
        "water":              [59, 130, 246, 200],
        "bare_soil":          [234, 179, 8, 180],
        "urban":              [239, 68, 68, 160],
        "vegetation_light":   [134, 239, 172, 180],
        "vegetation_dense":   [34, 197, 94, 220],
    }

    def get_full_image(self, layer: str, year: int, width: int = 800, height: int = 1024, classes: str = "all") -> bytes:
        """Render raster as clean colored PNG with transparent background.

        Args:
            classes: comma-separated class names to include, or "all".
                     Valid names: water, bare_soil, urban, vegetation_light, vegetation_dense
        """
        path = self._get_raster_path(layer, year)
        if not path.exists():
            raise FileNotFoundError(f"No data: {path}")

        with rasterio.open(str(path)) as src:
            data = src.read(1)

        # Parse which classes to show
        if classes == "all":
            active_classes = set(self.CLASS_COLORS.keys())
        else:
            active_classes = set(c.strip() for c in classes.split(",") if c.strip())

        # Create RGBA image with discrete land class colors
        h, w = data.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)

        if layer == "ndvi":
            # Water: blue
            if "water" in active_classes:
                mask = data < -0.1
                rgba[mask] = [59, 130, 246, 200]

            # Bare soil / very low: yellow
            if "bare_soil" in active_classes:
                mask = (data >= -0.1) & (data < 0.0)
                rgba[mask] = [234, 179, 8, 180]

            # Urban / low vegetation: red
            if "urban" in active_classes:
                mask = (data >= 0.0) & (data < 0.2)
                rgba[mask] = [239, 68, 68, 160]

            # Light vegetation: light green
            if "vegetation_light" in active_classes:
                mask = (data >= 0.2) & (data < 0.4)
                rgba[mask] = [134, 239, 172, 180]

            # Dense vegetation: green
            if "vegetation_dense" in active_classes:
                mask = data >= 0.4
                rgba[mask] = [34, 197, 94, 220]

            # No data: transparent
            nodata_mask = (data == 0) | np.isnan(data)
            rgba[nodata_mask] = [0, 0, 0, 0]

        elif layer == "change":
            # Loss: red
            mask = data < 0
            rgba[mask] = [239, 68, 68, 200]
            # Stable: transparent (don't show)
            # Gain: green
            mask = data > 0
            rgba[mask] = [34, 197, 94, 200]

        else:
            # Default: treat as NDVI
            mask = data >= 0.4
            rgba[mask] = [34, 197, 94, 200]
            mask = (data >= 0.2) & (data < 0.4)
            rgba[mask] = [134, 239, 172, 180]
            mask = (data >= 0.0) & (data < 0.2)
            rgba[mask] = [239, 68, 68, 160]

        # Convert to PNG using PIL (much cleaner than matplotlib)
        img = Image.fromarray(rgba, 'RGBA')
        if (h, w) != (height, width):
            img = img.resize((width, height), Image.NEAREST)

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf.getvalue()

    def get_tile(self, layer: str, year: int, z: int, x: int, y: int) -> bytes:
        """Get a single tile — for now returns full image (tile server TBD)."""
        return self.get_full_image(layer, year)

    def get_point_value(self, layer: str, year: int, lat: float, lon: float) -> float | None:
        """Get raster value at a specific lat/lon point."""
        path = self._get_raster_path(layer, year)
        if not path.exists():
            return None

        with rasterio.open(str(path)) as src:
            try:
                row, col = src.index(lon, lat)
                if 0 <= row < src.height and 0 <= col < src.width:
                    data = src.read(1)
                    return float(data[row, col])
            except Exception:
                pass
        return None

    def _get_raster_path(self, layer: str, year: int) -> Path:
        if layer == "ndvi":
            return self.ndvi_dir / f"ndvi_{year}.tif"
        elif layer == "change":
            # Find change file containing this year
            for f in self.change_dir.glob(f"change_*_{year}.tif"):
                return f
            return self.change_dir / f"change_{year-5}_{year}.tif"
        elif layer == "classification":
            return self.class_dir / f"classification_{year}.tif"
        return self.ndvi_dir / f"ndvi_{year}.tif"
