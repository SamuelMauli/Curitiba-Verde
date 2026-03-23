# CwbVerde Plan 6: Deploy to Hugging Face Spaces

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the complete CwbVerde application to Hugging Face Spaces with OAuth authentication for CRUD, persistent storage via HF Datasets API, and public URL access.

**Architecture:** HF Space running Streamlit SDK. Immutable data (COGs, Parquet) in HF Dataset repo. Mutable data (events, areas) synced via HF Datasets API. OAuth for write operations.

**Tech Stack:** huggingface_hub, Streamlit on HF Spaces

**Spec Reference:** `docs/superpowers/specs/2026-03-23-cwbverde-design.md` — Sections 9, 11

**Depends on:** Plans 1-5 (complete application)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/utils/hf_persistence.py` | HF Datasets API sync for mutable data |
| Create | `app/utils/auth.py` | HF Spaces OAuth wrapper |
| Create | `README.md` (HF Space format) | Space configuration |
| Modify | `events/database.py` | Add sync hooks |
| Modify | `app/pages/4_Eventos_Historia.py` | Add auth checks |

---

## Task 1: HF Persistence Layer

**Files:**
- Create: `app/utils/hf_persistence.py`

- [ ] **Step 1: Write persistence utilities**

```python
# app/utils/hf_persistence.py
"""Persistence layer for Hugging Face Spaces — sync mutable data."""
import os
import shutil
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download


HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "SamuelMauli/CwbVerde-userdata")
HF_DATA_REPO = os.environ.get("HF_DATA_REPO", "SamuelMauli/CwbVerde-data")


def sync_db_to_hub(db_path: str) -> bool:
    """Upload SQLite database to HF Dataset for persistence.

    Called after each write operation (create/update/delete event).
    """
    try:
        api = HfApi()
        api.upload_file(
            path_or_fileobj=db_path,
            path_in_repo="events.db",
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
        )
        return True
    except Exception as e:
        print(f"Warning: Failed to sync DB to Hub: {e}")
        return False


def restore_db_from_hub(db_path: str) -> bool:
    """Download SQLite database from HF Dataset on startup.

    Restores events and custom areas from last sync.
    """
    try:
        downloaded = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename="events.db",
            repo_type="dataset",
            local_dir=str(Path(db_path).parent),
        )
        if downloaded != db_path:
            shutil.copy(downloaded, db_path)
        return True
    except Exception:
        return False


def get_data_file_url(filename: str) -> str:
    """Get URL for a data file in the HF Data repo.

    Use for large files (COGs, Parquet) stored in a separate dataset.
    """
    return f"https://huggingface.co/datasets/{HF_DATA_REPO}/resolve/main/{filename}"
```

- [ ] **Step 2: Commit**

```bash
git add app/utils/hf_persistence.py
git commit -m "feat: add HF Datasets API persistence layer"
```

---

## Task 2: OAuth Authentication

**Files:**
- Create: `app/utils/auth.py`

- [ ] **Step 1: Write auth utilities**

```python
# app/utils/auth.py
"""Authentication wrapper for HF Spaces OAuth."""
import os
import streamlit as st


def is_running_on_hf_spaces() -> bool:
    """Check if running on Hugging Face Spaces."""
    return os.environ.get("SPACE_ID") is not None


def get_current_user() -> dict | None:
    """Get current logged-in user from HF Spaces OAuth.

    Returns dict with 'name', 'email', etc. or None if not logged in.
    """
    if not is_running_on_hf_spaces():
        # Local development: mock user
        return {"name": "dev_user", "email": "dev@local"}

    # HF Spaces provides user info via experimental API
    try:
        user = st.experimental_user
        if user and user.get("email"):
            return {"name": user.get("name", ""), "email": user["email"]}
    except Exception:
        pass
    return None


def require_auth(action: str = "esta ação") -> dict:
    """Require authentication for write operations.

    Shows login prompt if not authenticated.
    Returns user dict if authenticated.

    Usage:
        user = require_auth("adicionar evento")
        if user:
            # proceed with action
    """
    user = get_current_user()
    if user is None:
        st.warning(
            f"🔒 Você precisa estar logado para {action}. "
            "Faça login com sua conta Hugging Face."
        )
        return None
    return user
```

- [ ] **Step 2: Commit**

```bash
git add app/utils/auth.py
git commit -m "feat: add HF Spaces OAuth authentication wrapper"
```

---

## Task 3: Update Events Page with Auth

**Files:**
- Modify: `app/pages/4_Eventos_Historia.py`

- [ ] **Step 1: Add auth checks to CRUD operations**

Add auth import and wrap the form submission:

```python
# At the top, add:
from app.utils.auth import require_auth
from app.utils.hf_persistence import sync_db_to_hub

# Replace the form submission section:
    if submitted and ne_titulo:
        user = require_auth("adicionar evento")
        if user:
            db.create_event(
                data=str(ne_data), titulo=ne_titulo,
                categoria=ne_categoria, descricao=ne_descricao,
                fonte=ne_fonte, relevancia=ne_relevancia,
                criado_por=user["email"],
            )
            sync_db_to_hub(str(db_path))
            st.success(f"Evento '{ne_titulo}' adicionado!")
            st.rerun()
```

- [ ] **Step 2: Commit**

```bash
git add app/pages/4_Eventos_Historia.py
git commit -m "feat: add OAuth auth checks and HF sync to events CRUD"
```

---

## Task 4: HF Space README and Config

**Files:**
- Create: HF Space `README.md`

- [ ] **Step 1: Create Space README**

```markdown
---
title: CwbVerde — Mapeamento de Desmatamento de Curitiba
emoji: 🌳
colorFrom: green
colorTo: yellow
sdk: streamlit
sdk_version: 1.30.0
app_file: app/Home.py
pinned: false
license: mit
---

# CwbVerde 🌳

Sistema de mapeamento de desmatamento e cobertura vegetal de Curitiba-PR (2000-2024).

## Funcionalidades
- Mapas NDVI anuais com classificação de uso do solo
- Mapa interativo com desenho de polígonos e seleção de bairros
- Comparação entre áreas lado a lado
- Timeline de 3000+ eventos históricos de Curitiba
- Relatórios exportáveis (PDF, CSV)
- Análise de correlação eventos ↔ NDVI

## Tecnologias
- Pipeline: Python, Google Earth Engine, rasterio, scikit-learn, XGBoost
- Dashboard: Streamlit + React-Leaflet custom component
- Classificação: Ensemble (Random Forest + XGBoost + SVM)
- Dados: Landsat, Sentinel-2, MapBiomas, SRTM

## Autores
Trabalho Final — Processamento de Imagens e Sensoriamento Remoto
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "feat: add HF Spaces README with app configuration"
```

---

## Task 5: Database Startup Restoration

**Files:**
- Modify: `app/Home.py`

- [ ] **Step 1: Add DB restoration on startup**

Add at the top of Home.py, after imports:

```python
# Restore DB from HF Hub on startup
from app.utils.hf_persistence import restore_db_from_hub
from app.config import DATA_DIR

db_path = DATA_DIR / "events.db"
if not db_path.exists():
    restore_db_from_hub(str(db_path))
```

- [ ] **Step 2: Commit**

```bash
git add app/Home.py
git commit -m "feat: restore events DB from HF Hub on Space startup"
```

---

## Task 6: Create HF Space and Push

- [ ] **Step 1: Create HF Dataset repos**

```bash
# Create data repo (for large rasters)
huggingface-cli repo create CwbVerde-data --type dataset

# Create userdata repo (for mutable DB)
huggingface-cli repo create CwbVerde-userdata --type dataset
```

- [ ] **Step 2: Create HF Space**

```bash
huggingface-cli repo create CwbVerde --type space --space-sdk streamlit
```

- [ ] **Step 3: Add HF Space as remote and push**

```bash
cd /Users/samuelmauli/dev/CwbVerde
git remote add space https://huggingface.co/spaces/SamuelMauli/CwbVerde
git push space main
```

- [ ] **Step 4: Verify deployment**

Visit the Space URL and confirm:
- App loads without errors
- "Dados ainda não processados" message shows (expected — no data yet)
- Login flow works
- Events CRUD form appears

- [ ] **Step 5: Upload processed data (when pipeline has run)**

```bash
# Upload COGs and Parquet to data repo
huggingface-cli upload SamuelMauli/CwbVerde-data data/ndvi/ ndvi/ --repo-type dataset
huggingface-cli upload SamuelMauli/CwbVerde-data data/stats/ stats/ --repo-type dataset
huggingface-cli upload SamuelMauli/CwbVerde-data data/classification/ classification/ --repo-type dataset

# Seed events DB and upload
python -c "from events.database import EventsDB; db = EventsDB('data/events.db'); db.seed_from_json('events/seed_data/marcos_iniciais.json')"
huggingface-cli upload SamuelMauli/CwbVerde-userdata data/events.db events.db --repo-type dataset
```

---

## Summary

| Component | Status |
|-----------|--------|
| HF Persistence | Sync DB to/from HF Datasets API |
| OAuth | Read=public, Write=HF login required |
| Space config | README with Streamlit SDK |
| DB restore | Auto-restore from Hub on startup |
| Data hosting | COGs in HF Dataset, DB in separate HF Dataset |
| Deploy | Push to HF Spaces, verify |

---

## Post-Deploy Checklist

- [ ] Space loads without errors
- [ ] OAuth login works
- [ ] Events CRUD creates and persists events
- [ ] Map displays NDVI overlay (after data upload)
- [ ] Temporal evolution page shows charts
- [ ] Reports page generates PNG/CSV
- [ ] Public URL accessible
