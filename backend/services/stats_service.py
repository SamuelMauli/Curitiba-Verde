"""Statistics service — yearly stats, bairro stats, area stats."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
import rasterio
import json
from pipeline.config import DATA_DIR, PIXEL_AREA_HA


class StatsService:
    def get_yearly_stats(self) -> list[dict]:
        path = DATA_DIR / "stats" / "yearly_summary.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            return df.to_dict(orient="records")
        return []

    def get_bairro_stats(self, name: str, year: int) -> dict:
        path = DATA_DIR / "stats" / f"bairros_{year}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            row = df[df["nome"] == name]
            if not row.empty:
                return row.iloc[0].to_dict()
        return {"error": f"No data for {name}/{year}"}

    def get_area_stats(self, geojson: dict, year: int) -> dict:
        """Calculate stats for a custom polygon."""
        ndvi_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
        if not ndvi_path.exists():
            return {"error": f"No NDVI data for {year}"}

        try:
            from rasterio.mask import mask as rasterio_mask
            from shapely.geometry import shape

            geometry = shape(geojson)

            with rasterio.open(str(ndvi_path)) as src:
                out_image, out_transform = rasterio_mask(
                    src, [geojson], crop=True, nodata=0
                )
                ndvi = out_image[0]

            valid = ndvi[ndvi != 0]
            if len(valid) == 0:
                return {"error": "No valid pixels in area"}

            green_px = int((valid > 0.3).sum())
            return {
                "year": year,
                "ndvi_mean": float(valid.mean()),
                "ndvi_std": float(valid.std()),
                "ndvi_min": float(valid.min()),
                "ndvi_max": float(valid.max()),
                "green_pixels": green_px,
                "total_pixels": int(len(valid)),
                "green_area_ha": float(green_px * PIXEL_AREA_HA),
                "total_area_ha": float(len(valid) * PIXEL_AREA_HA),
                "green_percent": float(green_px / len(valid) * 100),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_bairros_geojson(self) -> dict:
        """Return bairros GeoJSON or fallback."""
        shp_dir = DATA_DIR / "shapefiles"

        # Try to find existing shapefile
        for ext in ["*.geojson", "*.json"]:
            for f in shp_dir.glob(ext):
                with open(f) as fp:
                    return json.load(fp)

        # Try shapefile via geopandas
        for f in shp_dir.glob("*.shp"):
            import geopandas as gpd
            gdf = gpd.read_file(str(f)).to_crs("EPSG:4326")
            return json.loads(gdf.to_json())

        # Fallback: generate approximate bairro boundaries for major areas
        return self._generate_fallback_bairros()

    def _generate_fallback_bairros(self) -> dict:
        """Generate approximate bairro GeoJSON for Curitiba."""
        # Major bairros with approximate centroids and bbox
        bairros = [
            {"name": "Centro", "lat": -25.4284, "lon": -49.2733, "r": 0.012},
            {"name": "Batel", "lat": -25.4420, "lon": -49.2900, "r": 0.010},
            {"name": "Água Verde", "lat": -25.4520, "lon": -49.2850, "r": 0.012},
            {"name": "Bigorrilho", "lat": -25.4350, "lon": -49.3000, "r": 0.010},
            {"name": "Portão", "lat": -25.4680, "lon": -49.2930, "r": 0.015},
            {"name": "Santa Felicidade", "lat": -25.3850, "lon": -49.3300, "r": 0.020},
            {"name": "Boqueirão", "lat": -25.4950, "lon": -49.2400, "r": 0.020},
            {"name": "Cajuru", "lat": -25.4600, "lon": -49.2250, "r": 0.018},
            {"name": "Boa Vista", "lat": -25.3800, "lon": -49.2600, "r": 0.018},
            {"name": "CIC", "lat": -25.4800, "lon": -49.3500, "r": 0.025},
            {"name": "Pinheirinho", "lat": -25.5100, "lon": -49.3100, "r": 0.018},
            {"name": "Tatuquara", "lat": -25.5400, "lon": -49.3200, "r": 0.020},
            {"name": "Cabral", "lat": -25.4050, "lon": -49.2650, "r": 0.008},
            {"name": "Juvevê", "lat": -25.4150, "lon": -49.2700, "r": 0.007},
            {"name": "Bacacheri", "lat": -25.3950, "lon": -49.2450, "r": 0.012},
            {"name": "Cristo Rei", "lat": -25.4350, "lon": -49.2500, "r": 0.008},
            {"name": "Jardim Botânico", "lat": -25.4430, "lon": -49.2380, "r": 0.010},
            {"name": "Rebouças", "lat": -25.4450, "lon": -49.2650, "r": 0.008},
            {"name": "Novo Mundo", "lat": -25.4900, "lon": -49.2750, "r": 0.012},
            {"name": "Hauer", "lat": -25.4780, "lon": -49.2650, "r": 0.010},
            {"name": "Uberaba", "lat": -25.4700, "lon": -49.2200, "r": 0.015},
            {"name": "Alto da XV", "lat": -25.4280, "lon": -49.2550, "r": 0.008},
            {"name": "Campina do Siqueira", "lat": -25.4450, "lon": -49.3100, "r": 0.010},
            {"name": "Mercês", "lat": -25.4250, "lon": -49.2950, "r": 0.008},
            {"name": "Pilarzinho", "lat": -25.3900, "lon": -49.2900, "r": 0.012},
            {"name": "Barreirinha", "lat": -25.3650, "lon": -49.2700, "r": 0.012},
            {"name": "Sítio Cercado", "lat": -25.5300, "lon": -49.2900, "r": 0.018},
            {"name": "Campo Comprido", "lat": -25.4500, "lon": -49.3300, "r": 0.015},
            {"name": "Ecoville", "lat": -25.4450, "lon": -49.3500, "r": 0.012},
            {"name": "Santa Cândida", "lat": -25.3550, "lon": -49.2500, "r": 0.015},
        ]

        features = []
        for b in bairros:
            r = b["r"]
            lat, lon = b["lat"], b["lon"]
            # Create hexagonal polygon
            import math
            coords = []
            for angle in range(0, 360, 60):
                rad = math.radians(angle)
                coords.append([
                    lon + r * math.cos(rad),
                    lat + r * 0.8 * math.sin(rad),
                ])
            coords.append(coords[0])  # close ring

            features.append({
                "type": "Feature",
                "properties": {"NOME": b["name"], "nome": b["name"]},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords],
                },
            })

        return {"type": "FeatureCollection", "features": features}
