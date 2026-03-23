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
                     bairros: list = None, regional: str = None,
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
                    bairro: str = None, limit: int = 1000) -> list:
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

    def list_custom_areas(self, criado_por: str = None) -> list:
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

    def list_comparisons(self) -> list:
        rows = self._conn.execute("SELECT * FROM comparacoes").fetchall()
        return [dict(r) for r in rows]

    def seed_from_json(self, json_path: str) -> int:
        """Load seed events from JSON file. Returns count of events added."""
        import json as json_module
        with open(json_path) as f:
            events = json_module.load(f)
        count = 0
        for e in events:
            self.create_event(**e)
            count += 1
        return count

    def close(self):
        self._conn.close()
