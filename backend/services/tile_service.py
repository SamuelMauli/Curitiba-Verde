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

        if layer == "classification":
            # Use real classification raster (classes 1-5)
            # 1=water, 2=dense_veg, 3=light_veg, 4=urban, 5=bare_soil
            CLASS_MAP = {
                1: ("water", [30, 100, 220, 220]),
                2: ("vegetation_dense", [22, 163, 74, 220]),
                3: ("vegetation_light", [134, 239, 172, 190]),
                4: ("urban", [220, 50, 50, 190]),
                5: ("bare_soil", [234, 179, 8, 190]),
            }
            for class_id, (class_name, color) in CLASS_MAP.items():
                if class_name in active_classes:
                    rgba[data == class_id] = color
            rgba[data == 0] = [0, 0, 0, 0]

        elif layer == "ndvi":
            # Use classification raster if available for better accuracy
            class_path = self.class_dir / f"classification_{year}.tif"
            if class_path.exists():
                with rasterio.open(str(class_path)) as csrc:
                    cdata = csrc.read(1)
                # Resize if needed
                if cdata.shape != data.shape:
                    from PIL import Image as PILImg
                    cimg = PILImg.fromarray(cdata)
                    cimg = cimg.resize((data.shape[1], data.shape[0]), PILImg.NEAREST)
                    cdata = np.array(cimg)

                CLASS_MAP = {
                    1: ("water", [30, 100, 220, 220]),
                    2: ("vegetation_dense", [22, 163, 74, 220]),
                    3: ("vegetation_light", [134, 239, 172, 190]),
                    4: ("urban", [220, 50, 50, 190]),
                    5: ("bare_soil", [234, 179, 8, 190]),
                }
                for class_id, (class_name, color) in CLASS_MAP.items():
                    if class_name in active_classes:
                        rgba[cdata == class_id] = color
                rgba[cdata == 0] = [0, 0, 0, 0]
            else:
                # Fallback: simple NDVI thresholds
                if "water" in active_classes:
                    rgba[data < -0.1] = [30, 100, 220, 220]
                if "bare_soil" in active_classes:
                    rgba[(data >= -0.1) & (data < 0.0)] = [234, 179, 8, 190]
                if "urban" in active_classes:
                    rgba[(data >= 0.0) & (data < 0.2)] = [220, 50, 50, 190]
                if "vegetation_light" in active_classes:
                    rgba[(data >= 0.2) & (data < 0.4)] = [134, 239, 172, 190]
                if "vegetation_dense" in active_classes:
                    rgba[data >= 0.4] = [22, 163, 74, 220]
                nodata_mask = (data == 0) | np.isnan(data)
                rgba[nodata_mask] = [0, 0, 0, 0]

        elif layer == "change":
            mask = data < 0
            rgba[mask] = [239, 68, 68, 200]
            mask = data > 0
            rgba[mask] = [34, 197, 94, 200]

        else:
            # Default: treat as classification if available
            class_path = self.class_dir / f"classification_{year}.tif"
            if class_path.exists():
                with rasterio.open(str(class_path)) as csrc:
                    cdata = csrc.read(1)
                CLASS_MAP = {
                    1: ("water", [30, 100, 220, 220]),
                    2: ("vegetation_dense", [22, 163, 74, 220]),
                    3: ("vegetation_light", [134, 239, 172, 190]),
                    4: ("urban", [220, 50, 50, 190]),
                    5: ("bare_soil", [234, 179, 8, 190]),
                }
                for class_id, (class_name, color) in CLASS_MAP.items():
                    if class_name in active_classes:
                        rgba[cdata == class_id] = color

        # Convert to PNG using PIL (much cleaner than matplotlib)
        img = Image.fromarray(rgba, 'RGBA')
        if (h, w) != (height, width):
            img = img.resize((width, height), Image.NEAREST)

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf.getvalue()

    def get_rgb_image(self, year: int, width: int = 800, height: int = 1024) -> bytes:
        """Render real satellite RGB image from composite bands (Red, Green, Blue)."""
        raw_dir = DATA_DIR / "raw"
        path = raw_dir / f"composite_{year}.tif"
        if not path.exists():
            raise FileNotFoundError(f"No composite for {year}")

        with rasterio.open(str(path)) as src:
            # Bands: blue(1), green(2), red(3), nir(4), swir1(5), swir2(6)
            red = src.read(3).astype(np.float64)
            green = src.read(2).astype(np.float64)
            blue = src.read(1).astype(np.float64)

        # Normalize to 0-255 with histogram stretch
        def stretch(band):
            valid = band[~np.isnan(band) & (band != 0)]
            if len(valid) == 0:
                return np.zeros_like(band, dtype=np.uint8)
            p2, p98 = np.percentile(valid, [2, 98])
            stretched = np.clip((band - p2) / (p98 - p2) * 255, 0, 255)
            stretched[np.isnan(band)] = 0
            return stretched.astype(np.uint8)

        r = stretch(red)
        g = stretch(green)
        b = stretch(blue)

        # Create alpha (transparent where nodata)
        alpha = np.where((red == 0) & (green == 0) & (blue == 0), 0, 220).astype(np.uint8)
        alpha[np.isnan(red)] = 0

        h, w = r.shape
        rgba = np.stack([r, g, b, alpha], axis=-1)

        img = Image.fromarray(rgba, 'RGBA')
        if (h, w) != (height, width):
            img = img.resize((width, height), Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format='PNG', optimize=True)
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
