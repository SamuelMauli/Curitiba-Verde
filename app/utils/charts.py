import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
# app/utils/charts.py
"""Plotly chart builders for the dashboard."""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from app.config import CLASS_COLORS, CLASS_NAMES, NDVI_COLORSCALE


def create_ndvi_timeseries(df: pd.DataFrame, title: str = "Evolução do NDVI") -> go.Figure:
    """Create NDVI time series line chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["ndvi_mean"],
        mode="lines+markers",
        name="NDVI médio",
        line=dict(color="#2E7D32", width=3),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(46, 125, 50, 0.1)",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Ano",
        yaxis_title="NDVI médio",
        yaxis_range=[0, 1],
        template="plotly_white",
        height=400,
    )
    return fig


def create_green_area_timeseries(df: pd.DataFrame) -> go.Figure:
    """Create green area (hectares) time series."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["year"], y=df["green_area_ha"],
        marker_color="#66BB6A",
        name="Área verde (ha)",
    ))
    fig.update_layout(
        title="Área Verde ao Longo dos Anos",
        xaxis_title="Ano",
        yaxis_title="Hectares",
        template="plotly_white",
        height=350,
    )
    return fig


def create_class_distribution_pie(class_dist: dict, year: int) -> go.Figure:
    """Pie chart of land cover classes for a year."""
    names = list(class_dist.keys())
    values = [v["hectares"] for v in class_dist.values()]
    colors = [CLASS_COLORS.get(i + 1, "#999") for i in range(len(names))]
    fig = go.Figure(data=[go.Pie(
        labels=names, values=values,
        marker_colors=colors,
        hole=0.4,
    )])
    fig.update_layout(
        title=f"Uso do Solo — {year}",
        template="plotly_white",
        height=350,
    )
    return fig


def create_bairro_ranking(df: pd.DataFrame, metric: str = "ndvi_mean") -> go.Figure:
    """Horizontal bar chart ranking bairros by metric."""
    sorted_df = df.sort_values(metric, ascending=True).tail(20)
    fig = go.Figure(go.Bar(
        x=sorted_df[metric],
        y=sorted_df["nome"],
        orientation="h",
        marker_color="#2E7D32",
    ))
    fig.update_layout(
        title=f"Top 20 Bairros — {metric}",
        xaxis_title=metric,
        template="plotly_white",
        height=600,
    )
    return fig


def create_comparison_chart(
    data_a: pd.DataFrame, data_b: pd.DataFrame,
    label_a: str, label_b: str,
) -> go.Figure:
    """Dual line chart comparing two areas over time."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data_a["year"], y=data_a["ndvi_mean"],
        name=label_a, line=dict(color="#2E7D32", width=3),
    ))
    fig.add_trace(go.Scatter(
        x=data_b["year"], y=data_b["ndvi_mean"],
        name=label_b, line=dict(color="#F44336", width=3),
    ))
    fig.update_layout(
        title="Comparação NDVI",
        xaxis_title="Ano", yaxis_title="NDVI médio",
        template="plotly_white", height=400,
    )
    return fig


def create_event_timeline(events: list[dict]) -> go.Figure:
    """Create visual timeline of events with color by category."""
    category_colors = {
        "legislacao": "#1565C0",
        "parque_area_verde": "#2E7D32",
        "obra_infraestrutura": "#F44336",
        "empreendimento": "#FF9800",
        "desastre_ambiental": "#B71C1C",
        "politica_publica": "#7B1FA2",
        "licenciamento": "#FF6F00",
        "transporte": "#00838F",
        "demografico": "#546E7A",
        "educacao_cultura": "#4527A0",
    }
    fig = go.Figure()
    for event in events:
        color = category_colors.get(event.get("categoria", ""), "#999")
        fig.add_trace(go.Scatter(
            x=[event["data"]],
            y=[event.get("categoria", "")],
            mode="markers",
            marker=dict(size=12, color=color),
            text=event["titulo"],
            hovertemplate="%{text}<br>%{x}<extra></extra>",
            showlegend=False,
        ))
    fig.update_layout(
        title="Timeline de Eventos",
        template="plotly_white",
        height=400,
        yaxis_title="Categoria",
    )
    return fig
