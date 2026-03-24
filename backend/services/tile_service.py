"""Tile service — serves map tiles from COG rasters."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import rasterio
from io import BytesIO
from pipeline.config import DATA_DIR
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


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

    def get_full_image(self, layer: str, year: int, width: int = 800, height: int = 1024) -> bytes:
        """Render full raster as colored PNG."""
        path = self._get_raster_path(layer, year)
        if not path.exists():
            raise FileNotFoundError(f"No data: {path}")

        with rasterio.open(str(path)) as src:
            data = src.read(1)

        fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)

        if layer == "ndvi":
            cmap = plt.cm.RdYlGn
            im = ax.imshow(data, cmap=cmap, vmin=-0.2, vmax=0.8)
        elif layer == "change":
            colors_map = np.zeros((*data.shape, 4))
            colors_map[data < 0] = [0.9, 0.1, 0.1, 0.8]
            colors_map[data == 0] = [0.5, 0.5, 0.5, 0.2]
            colors_map[data > 0] = [0.1, 0.8, 0.1, 0.8]
            ax.imshow(colors_map)
        else:
            ax.imshow(data, cmap="RdYlGn", vmin=-0.2, vmax=0.8)

        ax.axis("off")
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", pad_inches=0, transparent=True)
        plt.close()
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
