# CwbVerde Plan 3: Events System — Database, Scrapers, Correlation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the historical events system with SQLite database, CRUD operations, web scrapers for automated data collection from public sources, seed data with curated marcos, and NDVI correlation analysis.

**Architecture:** SQLite database with 3 tables (eventos, areas_customizadas, comparacoes). Scrapers collect events from Diário Oficial, IPPUC, MapBiomas Alertas, and IBGE. Correlation module links events to NDVI changes.

**Tech Stack:** Python 3.10+, sqlite3, requests, beautifulsoup4, pandas, pytest

**Spec Reference:** `docs/superpowers/specs/2026-03-23-cwbverde-design.md` — Sections 4, 11

**Depends on:** Nothing (can be developed in parallel with Plans 1-2)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `events/__init__.py` | Package init |
| Create | `events/database.py` | SQLite CRUD for all 3 tables |
| Create | `events/scrapers/__init__.py` | Package init |
| Create | `events/scrapers/diario_oficial.py` | Scraper for Curitiba Diário Oficial |
| Create | `events/scrapers/mapbiomas_alertas.py` | MapBiomas Alertas API client |
| Create | `events/scrapers/ippuc_dados.py` | IPPUC open data client |
| Create | `events/scrapers/ibge_censos.py` | IBGE SIDRA API client |
| Create | `events/correlation.py` | Event ↔ NDVI delta correlation |
| Create | `events/seed_data/marcos_iniciais.json` | 15 curated initial marcos |
| Create | `tests/test_events_db.py` | Test CRUD operations |
| Create | `tests/test_correlation.py` | Test NDVI correlation |

---

## Task 1: SQLite Database with Full CRUD

**Files:**
- Create: `events/database.py`
- Create: `tests/test_events_db.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_events_db.py
import pytest
import json
from events.database import EventsDB


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test_events.db")
    return EventsDB(db_path)


class TestEventsCRUD:
    def test_create_event(self, db):
        event_id = db.create_event(
            data="2020-01-15",
            titulo="Criação do Parque Linear",
            descricao="Novo parque ao longo do Rio Belém",
            categoria="parque_area_verde",
            fonte="Diário Oficial",
            bairros=["Centro", "Alto da XV"],
            regional="Matriz",
            impacto_ndvi="positivo",
            relevancia=4,
        )
        assert event_id > 0

    def test_read_event(self, db):
        eid = db.create_event(
            data="2020-01-15", titulo="Teste",
            categoria="legislacao",
        )
        event = db.get_event(eid)
        assert event["titulo"] == "Teste"
        assert event["categoria"] == "legislacao"

    def test_update_event(self, db):
        eid = db.create_event(
            data="2020-01-15", titulo="Original",
            categoria="legislacao",
        )
        db.update_event(eid, titulo="Atualizado")
        event = db.get_event(eid)
        assert event["titulo"] == "Atualizado"

    def test_delete_event(self, db):
        eid = db.create_event(
            data="2020-01-15", titulo="Deletar",
            categoria="legislacao",
        )
        db.delete_event(eid)
        assert db.get_event(eid) is None

    def test_list_events_by_category(self, db):
        db.create_event(data="2020-01-01", titulo="A", categoria="legislacao")
        db.create_event(data="2020-02-01", titulo="B", categoria="parque_area_verde")
        db.create_event(data="2020-03-01", titulo="C", categoria="legislacao")
        events = db.list_events(categoria="legislacao")
        assert len(events) == 2

    def test_list_events_by_year(self, db):
        db.create_event(data="2019-06-01", titulo="A", categoria="legislacao")
        db.create_event(data="2020-06-01", titulo="B", categoria="legislacao")
        events = db.list_events(year=2020)
        assert len(events) == 1

    def test_list_events_by_bairro(self, db):
        db.create_event(
            data="2020-01-01", titulo="A", categoria="obra_infraestrutura",
            bairros=["Centro", "Batel"],
        )
        db.create_event(
            data="2020-02-01", titulo="B", categoria="obra_infraestrutura",
            bairros=["Santa Felicidade"],
        )
        events = db.list_events(bairro="Centro")
        assert len(events) == 1

    def test_count_events(self, db):
        for i in range(5):
            db.create_event(data=f"2020-0{i+1}-01", titulo=f"E{i}", categoria="legislacao")
        assert db.count_events() == 5


class TestAreasCRUD:
    def test_create_custom_area(self, db):
        aid = db.create_custom_area(
            nome="Minha Área",
            geojson='{"type":"Polygon","coordinates":[[[-49.3,-25.5],[-49.2,-25.5],[-49.2,-25.4],[-49.3,-25.4],[-49.3,-25.5]]]}',
            criado_por="user@example.com",
        )
        assert aid > 0

    def test_list_custom_areas(self, db):
        db.create_custom_area(nome="A", geojson="{}", criado_por="user")
        db.create_custom_area(nome="B", geojson="{}", criado_por="user")
        areas = db.list_custom_areas()
        assert len(areas) == 2


class TestComparacoesCRUD:
    def test_create_comparison(self, db):
        cid = db.create_comparison(
            nome="Centro vs Batel",
            area_a_tipo="bairro", area_a_ref="Centro",
            area_b_tipo="bairro", area_b_ref="Batel",
            ano_a=2000, ano_b=2024,
            criado_por="user@example.com",
        )
        assert cid > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_events_db.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# events/database.py
"""SQLite database for events, custom areas, and comparisons."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime


class EventsDB:
    """CRUD operations for the CwbVerde events system."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data DATE NOT NULL,
                titulo TEXT NOT NULL,
                descricao TEXT,
                categoria TEXT NOT NULL,
                subcategoria TEXT,
                fonte TEXT,
                url_fonte TEXT,
                bairros TEXT,
                regional TEXT,
                coordenadas TEXT,
                impacto_ndvi TEXT DEFAULT 'neutro',
                relevancia INTEGER DEFAULT 1,
                criado_por TEXT DEFAULT 'sistema',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS areas_customizadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                geojson TEXT NOT NULL,
                criado_por TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS comparacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                area_a_tipo TEXT NOT NULL,
                area_a_ref TEXT NOT NULL,
                area_b_tipo TEXT NOT NULL,
                area_b_ref TEXT NOT NULL,
                ano_a INTEGER,
                ano_b INTEGER,
                camada TEXT DEFAULT 'ndvi',
                criado_por TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self._conn.commit()

    # ── Eventos CRUD ──

    def create_event(self, data: str, titulo: str, categoria: str,
                     descricao: str = None, subcategoria: str = None,
                     fonte: str = None, url_fonte: str = None,
                     bairros: list[str] = None, regional: str = None,
                     coordenadas: dict = None, impacto_ndvi: str = "neutro",
                     relevancia: int = 1, criado_por: str = "sistema") -> int:
        cursor = self._conn.execute(
            """INSERT INTO eventos
               (data, titulo, descricao, categoria, subcategoria, fonte,
                url_fonte, bairros, regional, coordenadas, impacto_ndvi,
                relevancia, criado_por)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data, titulo, descricao, categoria, subcategoria, fonte,
             url_fonte, json.dumps(bairros) if bairros else None,
             regional, json.dumps(coordenadas) if coordenadas else None,
             impacto_ndvi, relevancia, criado_por),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_event(self, event_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM eventos WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("bairros"):
            d["bairros"] = json.loads(d["bairros"])
        if d.get("coordenadas"):
            d["coordenadas"] = json.loads(d["coordenadas"])
        return d

    def update_event(self, event_id: int, **kwargs) -> None:
        if "bairros" in kwargs and isinstance(kwargs["bairros"], list):
            kwargs["bairros"] = json.dumps(kwargs["bairros"])
        if "coordenadas" in kwargs and isinstance(kwargs["coordenadas"], dict):
            kwargs["coordenadas"] = json.dumps(kwargs["coordenadas"])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [event_id]
        self._conn.execute(f"UPDATE eventos SET {sets} WHERE id = ?", values)
        self._conn.commit()

    def delete_event(self, event_id: int) -> None:
        self._conn.execute("DELETE FROM eventos WHERE id = ?", (event_id,))
        self._conn.commit()

    def list_events(self, categoria: str = None, year: int = None,
                    bairro: str = None, limit: int = 1000) -> list[dict]:
        query = "SELECT * FROM eventos WHERE 1=1"
        params = []
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        if year:
            query += " AND strftime('%Y', data) = ?"
            params.append(str(year))
        if bairro:
            query += " AND bairros LIKE ?"
            params.append(f'%"{bairro}"%')
        query += " ORDER BY data ASC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            if d.get("bairros"):
                d["bairros"] = json.loads(d["bairros"])
            results.append(d)
        return results

    def count_events(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM eventos").fetchone()[0]

    # ── Areas Customizadas CRUD ──

    def create_custom_area(self, nome: str, geojson: str,
                           criado_por: str) -> int:
        cursor = self._conn.execute(
            "INSERT INTO areas_customizadas (nome, geojson, criado_por) VALUES (?, ?, ?)",
            (nome, geojson, criado_por),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_custom_areas(self, criado_por: str = None) -> list[dict]:
        if criado_por:
            rows = self._conn.execute(
                "SELECT * FROM areas_customizadas WHERE criado_por = ?",
                (criado_por,),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM areas_customizadas").fetchall()
        return [dict(r) for r in rows]

    # ── Comparacoes CRUD ──

    def create_comparison(self, nome: str, area_a_tipo: str, area_a_ref: str,
                          area_b_tipo: str, area_b_ref: str,
                          ano_a: int = None, ano_b: int = None,
                          camada: str = "ndvi", criado_por: str = "sistema") -> int:
        cursor = self._conn.execute(
            """INSERT INTO comparacoes
               (nome, area_a_tipo, area_a_ref, area_b_tipo, area_b_ref,
                ano_a, ano_b, camada, criado_por)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, area_a_tipo, area_a_ref, area_b_tipo, area_b_ref,
             ano_a, ano_b, camada, criado_por),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_comparisons(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM comparacoes").fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_events_db.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add events/__init__.py events/database.py tests/test_events_db.py
git commit -m "feat: add SQLite database with full CRUD for events, areas, comparisons"
```

---

## Task 2: Seed Data (Curated Initial Marcos)

**Files:**
- Create: `events/seed_data/marcos_iniciais.json`

- [ ] **Step 1: Create seed file with 15 curated marcos**

```json
[
  {
    "data": "2000-06-19",
    "titulo": "Lei Municipal 10.237 — Plano Diretor de Curitiba",
    "descricao": "Aprovação do Plano Diretor que define zoneamento e áreas de preservação ambiental",
    "categoria": "legislacao",
    "fonte": "Câmara Municipal de Curitiba",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "positivo",
    "relevancia": 5
  },
  {
    "data": "2001-03-15",
    "titulo": "Inauguração do Parque Tanguá — ampliação",
    "descricao": "Ampliação do Parque Tanguá com novas áreas verdes e infraestrutura",
    "categoria": "parque_area_verde",
    "fonte": "Prefeitura de Curitiba",
    "bairros": ["Pilarzinho", "Taboão"],
    "regional": "Santa Felicidade",
    "impacto_ndvi": "positivo",
    "relevancia": 4
  },
  {
    "data": "2003-09-01",
    "titulo": "Início obras Linha Verde (BR-116)",
    "descricao": "Transformação da BR-116 em via urbana com BRT, removendo vegetação lateral",
    "categoria": "obra_infraestrutura",
    "fonte": "IPPUC",
    "bairros": ["Prado Velho", "Hauer", "Fanny", "Novo Mundo"],
    "regional": "Portão",
    "impacto_ndvi": "negativo",
    "relevancia": 5
  },
  {
    "data": "2004-12-01",
    "titulo": "Criação do Bosque do Alemão",
    "descricao": "Novo bosque urbano no bairro Vista Alegre",
    "categoria": "parque_area_verde",
    "fonte": "SMMA Curitiba",
    "bairros": ["Vista Alegre"],
    "regional": "Boa Vista",
    "impacto_ndvi": "positivo",
    "relevancia": 3
  },
  {
    "data": "2007-04-10",
    "titulo": "Shopping Palladium inaugurado",
    "descricao": "Um dos maiores shoppings do sul do Brasil, construído em área anteriormente verde",
    "categoria": "empreendimento",
    "fonte": "Gazeta do Povo",
    "bairros": ["Portão"],
    "regional": "Portão",
    "impacto_ndvi": "negativo",
    "relevancia": 4
  },
  {
    "data": "2008-11-01",
    "titulo": "Programa Biocidade lançado",
    "descricao": "Programa municipal de sustentabilidade urbana com metas de arborização",
    "categoria": "politica_publica",
    "fonte": "Prefeitura de Curitiba",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "positivo",
    "relevancia": 4
  },
  {
    "data": "2010-08-01",
    "titulo": "Censo IBGE 2010 — Curitiba: 1.751.907 habitantes",
    "descricao": "Censo demográfico registra crescimento populacional de 10% desde 2000",
    "categoria": "demografico",
    "fonte": "IBGE",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "neutro",
    "relevancia": 5
  },
  {
    "data": "2012-06-15",
    "titulo": "Lei Municipal 13.899 — IPTU Verde",
    "descricao": "Desconto no IPTU para imóveis com área verde preservada",
    "categoria": "politica_publica",
    "fonte": "Câmara Municipal de Curitiba",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "positivo",
    "relevancia": 5
  },
  {
    "data": "2014-06-01",
    "titulo": "Arena da Baixada — Copa do Mundo FIFA",
    "descricao": "Reforma e ampliação do estádio para a Copa, com impacto na área urbana do entorno",
    "categoria": "obra_infraestrutura",
    "fonte": "Gazeta do Povo",
    "bairros": ["Água Verde"],
    "regional": "Portão",
    "impacto_ndvi": "negativo",
    "relevancia": 4
  },
  {
    "data": "2015-12-01",
    "titulo": "Revisão do Plano Diretor — Lei 14.771/2015",
    "descricao": "Nova revisão do Plano Diretor com ênfase em sustentabilidade e adensamento ao longo de eixos",
    "categoria": "legislacao",
    "fonte": "IPPUC",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "positivo",
    "relevancia": 5
  },
  {
    "data": "2017-03-01",
    "titulo": "Início obras do Ligeirão Leste-Oeste",
    "descricao": "Nova linha de BRT conectando bairros leste e oeste, com remoção de canteiros",
    "categoria": "transporte",
    "fonte": "URBS Curitiba",
    "bairros": ["Campina do Siqueira", "CIC", "Pinheirinho"],
    "regional": "CIC",
    "impacto_ndvi": "negativo",
    "relevancia": 3
  },
  {
    "data": "2019-01-01",
    "titulo": "Programa de Plantio de 100 mil árvores",
    "descricao": "Meta municipal de plantar 100 mil árvores em 4 anos",
    "categoria": "politica_publica",
    "fonte": "SMMA Curitiba",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "positivo",
    "relevancia": 4
  },
  {
    "data": "2020-03-15",
    "titulo": "Pandemia COVID-19 — lockdown",
    "descricao": "Redução de atividade de construção civil durante lockdown — possível recuperação vegetal temporária",
    "categoria": "politica_publica",
    "fonte": "Prefeitura de Curitiba",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "positivo",
    "relevancia": 3
  },
  {
    "data": "2022-08-01",
    "titulo": "Censo IBGE 2022 — Curitiba: 1.773.733 habitantes",
    "descricao": "Crescimento populacional desacelera, mas pressão urbana continua",
    "categoria": "demografico",
    "fonte": "IBGE",
    "bairros": [],
    "regional": "Todas",
    "impacto_ndvi": "neutro",
    "relevancia": 5
  },
  {
    "data": "2023-06-01",
    "titulo": "Inauguração do Parque de Bolso do Batel",
    "descricao": "Micro parque urbano em área anteriormente degradada",
    "categoria": "parque_area_verde",
    "fonte": "SMMA Curitiba",
    "bairros": ["Batel"],
    "regional": "Matriz",
    "impacto_ndvi": "positivo",
    "relevancia": 2
  }
]
```

- [ ] **Step 2: Create seed loading function**

Add to `events/database.py`:

```python
def seed_from_json(self, json_path: str) -> int:
    """Load seed events from JSON file. Returns count of events added."""
    import json
    with open(json_path) as f:
        events = json.load(f)
    count = 0
    for e in events:
        self.create_event(**e)
        count += 1
    return count
```

- [ ] **Step 3: Commit**

```bash
git add events/seed_data/marcos_iniciais.json
git commit -m "feat: add 15 curated seed events for Curitiba historical timeline"
```

---

## Task 3: NDVI Correlation Module

**Files:**
- Create: `events/correlation.py`
- Create: `tests/test_correlation.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_correlation.py
import numpy as np
import pytest
from events.correlation import (
    compute_event_ndvi_impact, compute_category_correlation,
)


class TestEventNDVIImpact:
    def test_negative_impact_detected(self):
        """NDVI drops after event → negative impact."""
        ndvi_before = 0.65
        ndvi_after = 0.40
        impact = compute_event_ndvi_impact(ndvi_before, ndvi_after, threshold=0.05)
        assert impact["direction"] == "negativo"
        assert impact["delta"] == pytest.approx(-0.25, abs=0.01)

    def test_positive_impact_detected(self):
        ndvi_before = 0.30
        ndvi_after = 0.55
        impact = compute_event_ndvi_impact(ndvi_before, ndvi_after, threshold=0.05)
        assert impact["direction"] == "positivo"

    def test_neutral_below_threshold(self):
        ndvi_before = 0.50
        ndvi_after = 0.48
        impact = compute_event_ndvi_impact(ndvi_before, ndvi_after, threshold=0.05)
        assert impact["direction"] == "neutro"


class TestCategoryCorrelation:
    def test_returns_per_category_stats(self):
        events = [
            {"categoria": "obra_infraestrutura", "delta_ndvi": -0.15},
            {"categoria": "obra_infraestrutura", "delta_ndvi": -0.20},
            {"categoria": "parque_area_verde", "delta_ndvi": 0.10},
            {"categoria": "parque_area_verde", "delta_ndvi": 0.15},
        ]
        result = compute_category_correlation(events)
        assert result["obra_infraestrutura"]["mean_delta"] < 0
        assert result["parque_area_verde"]["mean_delta"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_correlation.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# events/correlation.py
"""Correlate historical events with NDVI changes."""
import numpy as np
from collections import defaultdict


def compute_event_ndvi_impact(
    ndvi_before: float,
    ndvi_after: float,
    threshold: float = 0.05,
) -> dict:
    """Compute NDVI impact of a single event.

    Compares mean NDVI of affected area 1 year before vs 1 year after.

    Args:
        ndvi_before: Mean NDVI of area 1 year before event.
        ndvi_after: Mean NDVI of area 1 year after event.
        threshold: Minimum delta to count as impact.

    Returns:
        Dict with delta, direction, significance.
    """
    delta = ndvi_after - ndvi_before
    if delta < -threshold:
        direction = "negativo"
    elif delta > threshold:
        direction = "positivo"
    else:
        direction = "neutro"

    return {
        "delta": float(delta),
        "direction": direction,
        "ndvi_before": float(ndvi_before),
        "ndvi_after": float(ndvi_after),
        "significant": abs(delta) > threshold,
    }


def compute_category_correlation(
    events_with_delta: list[dict],
) -> dict:
    """Compute mean NDVI impact per event category.

    Args:
        events_with_delta: List of dicts with 'categoria' and 'delta_ndvi' keys.

    Returns:
        Dict keyed by category with mean_delta, count, std_delta.
    """
    by_category = defaultdict(list)
    for e in events_with_delta:
        by_category[e["categoria"]].append(e["delta_ndvi"])

    result = {}
    for cat, deltas in by_category.items():
        arr = np.array(deltas)
        result[cat] = {
            "mean_delta": float(arr.mean()),
            "std_delta": float(arr.std()) if len(arr) > 1 else 0.0,
            "count": len(arr),
            "negative_count": int((arr < -0.05).sum()),
            "positive_count": int((arr > 0.05).sum()),
        }
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_correlation.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add events/correlation.py tests/test_correlation.py
git commit -m "feat: add event-NDVI correlation analysis"
```

---

## Task 4: Scrapers (Stubs with Structure)

**Files:**
- Create: `events/scrapers/diario_oficial.py`
- Create: `events/scrapers/mapbiomas_alertas.py`
- Create: `events/scrapers/ippuc_dados.py`
- Create: `events/scrapers/ibge_censos.py`

Note: Full scraper implementation depends on target site structure at runtime. These are structured stubs with the correct interfaces that will be filled during execution.

- [ ] **Step 1: Create scraper interfaces**

```python
# events/scrapers/diario_oficial.py
"""Scraper for Curitiba Diário Oficial — legislation and licenses."""
import requests
from datetime import date


def search_diario_oficial(
    keywords: list[str],
    start_date: date,
    end_date: date,
    max_results: int = 100,
) -> list[dict]:
    """Search Curitiba Diário Oficial for events matching keywords.

    Keywords: zoneamento, supressão, parque, licenciamento, etc.

    Returns list of dicts with data, titulo, descricao, categoria, fonte, url_fonte.
    """
    # TODO: Implement actual scraping of legislacao.curitiba.pr.gov.br
    # Structure:
    # 1. Search by keyword in date range
    # 2. Parse results (title, date, type)
    # 3. Classify into event categories
    # 4. Return structured events
    return []
```

```python
# events/scrapers/mapbiomas_alertas.py
"""Client for MapBiomas Alertas API — deforestation alerts."""


def fetch_alerts_curitiba(
    start_year: int = 2000,
    end_year: int = 2024,
) -> list[dict]:
    """Fetch deforestation alerts for Curitiba from MapBiomas Alertas.

    Returns list of dicts with data, titulo, coordenadas, area_ha.
    """
    # TODO: Implement MapBiomas Alertas API integration
    # API: https://alertas.mapbiomas.org/api
    # Filter by Curitiba municipality code (4106902)
    return []
```

```python
# events/scrapers/ippuc_dados.py
"""Client for IPPUC (Curitiba Urban Planning Institute) open data."""


def fetch_ippuc_indicators(
    start_year: int = 2000,
    end_year: int = 2024,
) -> list[dict]:
    """Fetch urban indicators and project data from IPPUC.

    Source: dados.ippuc.org.br

    Returns list of events derived from urban projects and indicators.
    """
    # TODO: Implement IPPUC data portal integration
    return []
```

```python
# events/scrapers/ibge_censos.py
"""Client for IBGE SIDRA API — census and demographic data."""
import requests


def fetch_census_data() -> list[dict]:
    """Fetch census milestones for Curitiba from IBGE SIDRA.

    Returns list of demographic events (census years, population milestones).
    """
    # TODO: Implement IBGE SIDRA API calls
    # API: https://apisidra.ibge.gov.br/
    # Table 6579 (population by municipality)
    return []
```

- [ ] **Step 2: Commit**

```bash
git add events/scrapers/__init__.py events/scrapers/diario_oficial.py events/scrapers/mapbiomas_alertas.py events/scrapers/ippuc_dados.py events/scrapers/ibge_censos.py
git commit -m "feat: add scraper stubs for Diário Oficial, MapBiomas, IPPUC, IBGE"
```

---

## Task 5: Run All Tests

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass.

---

## Summary

| Module | Status | Tests |
|--------|--------|-------|
| `events/database.py` | Full CRUD for 3 tables | `test_events_db.py` |
| `events/correlation.py` | Event↔NDVI impact | `test_correlation.py` |
| `events/seed_data/marcos_iniciais.json` | 15 curated marcos | — |
| `events/scrapers/*.py` | Structured stubs | — |

**Next plan:** `2026-03-23-cwbverde-plan-4-dashboard.md` (Dashboard Streamlit)
