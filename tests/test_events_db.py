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
            data="2020-01-15", titulo="Criação do Parque Linear",
            descricao="Novo parque ao longo do Rio Belém",
            categoria="parque_area_verde", fonte="Diário Oficial",
            bairros=["Centro", "Alto da XV"], regional="Matriz",
            impacto_ndvi="positivo", relevancia=4,
        )
        assert event_id > 0

    def test_read_event(self, db):
        eid = db.create_event(data="2020-01-15", titulo="Teste", categoria="legislacao")
        event = db.get_event(eid)
        assert event["titulo"] == "Teste"
        assert event["categoria"] == "legislacao"

    def test_update_event(self, db):
        eid = db.create_event(data="2020-01-15", titulo="Original", categoria="legislacao")
        db.update_event(eid, titulo="Atualizado")
        event = db.get_event(eid)
        assert event["titulo"] == "Atualizado"

    def test_delete_event(self, db):
        eid = db.create_event(data="2020-01-15", titulo="Deletar", categoria="legislacao")
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
        db.create_event(data="2020-01-01", titulo="A", categoria="obra_infraestrutura", bairros=["Centro", "Batel"])
        db.create_event(data="2020-02-01", titulo="B", categoria="obra_infraestrutura", bairros=["Santa Felicidade"])
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
            ano_a=2000, ano_b=2024, criado_por="user@example.com",
        )
        assert cid > 0
