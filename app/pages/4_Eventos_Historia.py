# app/pages/4_Eventos_Historia.py
"""Events and history page — timeline + CRUD."""
import streamlit as st
from events.database import EventsDB
from app.config import DATA_DIR

st.set_page_config(page_title="Eventos e História", page_icon="📜", layout="wide")
st.title("📜 Eventos e História de Curitiba")

db_path = DATA_DIR / "events.db"
db = EventsDB(str(db_path))

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    year_filter = st.selectbox("Ano:", [None] + list(range(2000, 2025)),
                                format_func=lambda x: "Todos" if x is None else str(x))
with col2:
    categories = [
        "legislacao", "parque_area_verde", "obra_infraestrutura",
        "empreendimento", "desastre_ambiental", "politica_publica",
        "licenciamento", "transporte", "demografico", "educacao_cultura",
    ]
    cat_filter = st.selectbox("Categoria:", [None] + categories,
                               format_func=lambda x: "Todas" if x is None else x)
with col3:
    st.metric("Total de Eventos", db.count_events())

# List events
events = db.list_events(year=year_filter, categoria=cat_filter, limit=200)

for event in events:
    impact_emoji = {"positivo": "🟢", "negativo": "🔴", "neutro": "⚪"}.get(
        event.get("impacto_ndvi", "neutro"), "⚪"
    )
    with st.expander(f'{impact_emoji} {event["data"]} — {event["titulo"]}'):
        st.write(f"**Categoria:** {event['categoria']}")
        if event.get("descricao"):
            st.write(event["descricao"])
        if event.get("bairros"):
            st.write(f"**Bairros:** {', '.join(event['bairros'])}")
        if event.get("fonte"):
            st.write(f"**Fonte:** {event['fonte']}")
        st.write(f"**Relevância:** {'⭐' * event.get('relevancia', 1)}")

# CRUD: Add new event
st.divider()
st.subheader("Adicionar Novo Evento")
with st.form("new_event"):
    ne_data = st.date_input("Data")
    ne_titulo = st.text_input("Título")
    ne_categoria = st.selectbox("Categoria", categories)
    ne_descricao = st.text_area("Descrição")
    ne_fonte = st.text_input("Fonte")
    ne_relevancia = st.slider("Relevância", 1, 5, 3)
    submitted = st.form_submit_button("Adicionar")
    if submitted and ne_titulo:
        db.create_event(
            data=str(ne_data), titulo=ne_titulo,
            categoria=ne_categoria, descricao=ne_descricao,
            fonte=ne_fonte, relevancia=ne_relevancia,
        )
        st.success(f"Evento '{ne_titulo}' adicionado!")
        st.rerun()

db.close()
