"""CwbVerde Backend — FastAPI with tile serving and REST API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
import numpy as np
import json


class UTF8JSONResponse(JSONResponse):
    """JSON response that ensures proper UTF-8 encoding for Portuguese characters."""
    media_type = "application/json; charset=utf-8"

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(
    title="CwbVerde API",
    version="2.0.0",
    default_response_class=UTF8JSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.services.tile_service import TileService
from backend.services.stats_service import StatsService
from backend.services.events_service import EventsService

tile_svc = TileService()
stats_svc = StatsService()
events_svc = EventsService()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/tiles/{layer}/{year}/{z}/{x}/{y}.png")
def get_tile(layer: str, year: int, z: int, x: int, y: int):
    """Serve map tiles from COG rasters via rio-tiler."""
    try:
        png_bytes = tile_svc.get_tile(layer, year, z, x, y)
        return Response(content=png_bytes, media_type="image/png")
    except FileNotFoundError:
        raise HTTPException(404, f"No data for {layer}/{year}")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/{layer}/{year}/image")
def get_layer_image(layer: str, year: int, width: int = 800, height: int = 1024, classes: str = "all"):
    """Get layer image with optional class filtering."""
    try:
        png_bytes = tile_svc.get_full_image(layer, year, width, height, classes=classes)
        return Response(content=png_bytes, media_type="image/png")
    except FileNotFoundError:
        raise HTTPException(404, f"No data for {layer}/{year}")


@app.get("/api/ndvi/{year}/point")
def get_ndvi_point(year: int, lat: float = Query(...), lon: float = Query(...)):
    """Get NDVI value at a specific point."""
    value = tile_svc.get_point_value("ndvi", year, lat, lon)
    return {"year": year, "lat": lat, "lon": lon, "ndvi": value}


@app.get("/api/stats/yearly")
def get_yearly_stats():
    """Get yearly summary statistics."""
    return stats_svc.get_yearly_stats()


@app.get("/api/stats/classification")
def get_classification_stats():
    """Get yearly classification statistics (water, vegetation, urban, etc)."""
    return stats_svc.get_classification_stats()


@app.get("/api/stats/bairro/{name}/{year}")
def get_bairro_stats(name: str, year: int):
    """Get statistics for a specific bairro and year."""
    return stats_svc.get_bairro_stats(name, year)


@app.post("/api/stats/area")
async def get_area_stats(request: dict):
    """Get statistics for a custom polygon area."""
    geojson = request.get("geojson")
    year = request.get("year", 2023)
    if not geojson:
        raise HTTPException(400, "geojson required")
    return stats_svc.get_area_stats(geojson, year)


@app.get("/api/events")
def list_events(
    year: int = None,
    category: str = None,
    bairro: str = None,
    limit: int = 500,
):
    return events_svc.list_events(year=year, category=category, bairro=bairro, limit=limit)


@app.post("/api/events")
async def create_event(event: dict):
    return events_svc.create_event(event)


@app.get("/api/events/categories")
def get_categories():
    return events_svc.get_categories()


@app.get("/api/events/stats")
def get_event_stats():
    """Get event count by year and category."""
    return events_svc.get_event_stats()


@app.get("/api/bairros")
def get_bairros():
    """Get bairros GeoJSON."""
    return stats_svc.get_bairros_geojson()


@app.get("/api/years")
def get_available_years():
    """Get list of years with available data."""
    return tile_svc.get_available_years()
