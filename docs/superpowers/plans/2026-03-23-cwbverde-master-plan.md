# CwbVerde — Master Implementation Plan

> **For agentic workers:** Each sub-plan below is an independent unit. Execute them in order (1→6). Each plan has its own spec reference at `docs/superpowers/specs/2026-03-23-cwbverde-design.md`.

**Goal:** Build a complete deforestation mapping system for Curitiba (2000-2024) with ML classification, interactive dashboard, and historical event correlation.

**Execution Order:**

| # | Plan | Depends On | Deliverable |
|---|------|------------|-------------|
| 1 | Pipeline Core | Nothing | GEE ingest, preprocess, NDVI, features, COG export |
| 2 | ML Classification | Plan 1 | Ensemble RF+XGB+SVM, validation, change detection |
| 3 | Events System | Nothing (parallel with 1-2) | SQLite, scrapers, seed data, NDVI correlation |
| 4 | Dashboard Streamlit | Plans 1, 2, 3 | 6 pages, charts, reports |
| 5 | React Map Component | Plan 4 | Custom Leaflet, polygons, split-screen compare |
| 6 | Deploy HF Spaces | Plans 4, 5 | OAuth, persistence, publication |

**Parallelization:** Plans 1+2 and Plan 3 can be developed in parallel (independent subsystems).

**Plan files:**
- `2026-03-23-cwbverde-plan-1-pipeline.md` — Pipeline Core
- `2026-03-23-cwbverde-plan-2-classification.md` — ML Classification
- `2026-03-23-cwbverde-plan-3-events.md` — Events System
- `2026-03-23-cwbverde-plan-4-dashboard.md` — Dashboard Streamlit
- `2026-03-23-cwbverde-plan-5-map-component.md` — React Map Component
- `2026-03-23-cwbverde-plan-6-deploy.md` — Deploy HF Spaces
