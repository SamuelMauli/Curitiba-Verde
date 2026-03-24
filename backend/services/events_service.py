"""Events service — CRUD for historical events."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from events.database import EventsDB
from pipeline.config import DATA_DIR
from collections import Counter


class EventsService:
    def __init__(self):
        self.db = EventsDB(str(DATA_DIR / "events.db"))

    def list_events(self, year=None, category=None, bairro=None, limit=500) -> list[dict]:
        return self.db.list_events(categoria=category, year=year, bairro=bairro, limit=limit)

    def create_event(self, event: dict) -> dict:
        eid = self.db.create_event(**event)
        return {"id": eid, "status": "created"}

    def get_categories(self) -> list[dict]:
        categories = {
            "legislacao": {"label": "Legislação", "color": "#1565C0", "icon": "gavel"},
            "parque_area_verde": {"label": "Parques e Áreas Verdes", "color": "#2E7D32", "icon": "park"},
            "obra_infraestrutura": {"label": "Obras e Infraestrutura", "color": "#F44336", "icon": "construction"},
            "empreendimento": {"label": "Empreendimentos", "color": "#FF9800", "icon": "business"},
            "desastre_ambiental": {"label": "Desastres Ambientais", "color": "#B71C1C", "icon": "warning"},
            "politica_publica": {"label": "Políticas Públicas", "color": "#7B1FA2", "icon": "policy"},
            "licenciamento": {"label": "Licenciamento", "color": "#FF6F00", "icon": "description"},
            "transporte": {"label": "Transporte", "color": "#00838F", "icon": "directions_bus"},
            "demografico": {"label": "Demografia", "color": "#546E7A", "icon": "people"},
            "educacao_cultura": {"label": "Educação e Cultura", "color": "#4527A0", "icon": "school"},
        }
        return [{"id": k, **v} for k, v in categories.items()]

    def get_event_stats(self) -> dict:
        events = self.db.list_events(limit=10000)
        by_year = Counter()
        by_category = Counter()
        for e in events:
            year = e["data"][:4] if e.get("data") else "unknown"
            by_year[year] += 1
            by_category[e.get("categoria", "unknown")] += 1
        return {
            "total": len(events),
            "by_year": dict(sorted(by_year.items())),
            "by_category": dict(by_category),
        }
