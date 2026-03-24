<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/MapLibre_GL-396CB2?style=for-the-badge&logo=maplibre&logoColor=white" />
  <img src="https://img.shields.io/badge/Google_Earth_Engine-4285F4?style=for-the-badge&logo=google-earth&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

# CwbVerde — Sistema de Mapeamento de Desmatamento de Curitiba

> Sistema de visao computacional e sensoriamento remoto que mapeia a evolucao do desmatamento e cobertura vegetal de Curitiba-PR de **2000 a 2024**, combinando analise NDVI, classificacao supervisionada por ensemble de ML, dados MapBiomas e uma timeline rica de eventos historicos urbanos.

---

## Visao Geral

O **CwbVerde** e uma plataforma completa de monitoramento ambiental urbano que utiliza imagens de satelite (Landsat 5/8/9, Sentinel-2) e tecnicas de visao computacional para analisar 25 anos de evolucao da cobertura vegetal de Curitiba.

### Publico-alvo dual

| Publico | Uso |
|---------|-----|
| **Academico** | Trabalho final de Processamento de Imagens e Sensoriamento Remoto |
| **Planejamento publico** | Prototipo de ferramenta de gestao urbana para secretarias municipais, ONGs e urbanistas |

### Principais entregas

- Mapas NDVI anuais (2000-2024) em GeoTIFF e PNG
- Mapas de classificacao de uso do solo (5 classes) por ano
- Mapas de change detection (perda/ganho de vegetacao)
- Dashboard interativo com selecao de area, comparacao e timeline
- **1242 eventos historicos** de Curitiba correlacionados com NDVI
- API REST para integracao com outros sistemas

---

## Arquitetura do Sistema

O sistema se divide em 3 camadas independentes:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA 3: FRONTEND                           │
│         React 18 + MapLibre GL + Tailwind CSS + Recharts        │
│              Dashboard interativo (porta 3000)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────────────┐
│                    CAMADA 2: BACKEND API                        │
│              FastAPI + rio-tiler + SQLite                       │
│       Tile serving, stats, eventos (porta 8000)                 │
│                                                                 │
│   /api/tiles  /api/stats  /api/events  /api/ndvi  /api/bairros │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Leitura de arquivos
┌──────────────────────────▼──────────────────────────────────────┐
│               CAMADA 1: PIPELINE DE PROCESSAMENTO               │
│                      (execucao offline)                          │
│                                                                 │
│   GEE ──→ Pre-processamento ──→ Indices ──→ Classificacao ML   │
│                                    │              │             │
│                              Change Detection  Estatisticas     │
│                                    │              │             │
│                                    ▼              ▼             │
│                              COG TIFFs    Parquet + SQLite      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pipeline de Dados — Como Funciona

### 1. Coleta de Dados

O pipeline coleta imagens de satelite via **Google Earth Engine** utilizando autenticacao por service account.

| Parametro | Valor |
|-----------|-------|
| **Sensores** | Landsat 5 (2000-2012), Landsat 8 (2013-2020), Landsat 9 (2021-2024) |
| **Complemento** | Sentinel-2 (a partir de 2017) |
| **Composicao** | Mediana anual (junho-setembro, periodo seco = menos nuvens) |
| **Cobertura maxima de nuvens** | 20% |
| **Bounding box** | `-49.40, -25.65, -49.15, -25.33` (Curitiba-PR) |
| **Resolucao espacial** | 30 metros (Landsat) / 10 metros (Sentinel-2) |

**Colecoes do GEE utilizadas:**

```python
GEE_COLLECTIONS = {
    "landsat5":  "LANDSAT/LT05/C02/T1_L2",
    "landsat8":  "LANDSAT/LC08/C02/T1_L2",
    "landsat9":  "LANDSAT/LC09/C02/T1_L2",
    "sentinel2": "COPERNICUS/S2_SR_HARMONIZED",
    "srtm":      "USGS/SRTMGL1_003",
}
```

### 2. Pre-processamento

Cada imagem bruta passa por 4 etapas antes da analise:

| Etapa | Descricao | Detalhe tecnico |
|-------|-----------|-----------------|
| **Mascara de nuvens** | Remove pixels contaminados por nuvens e sombras | Banda `QA_PIXEL` (bit flags) |
| **Recorte** | Limita a imagem ao perimetro de Curitiba | Shapefile IPPUC |
| **Reprojecao** | Padroniza o sistema de coordenadas | SIRGAS 2000 UTM 22S (`EPSG:31982`) |
| **Harmonizacao** | Normaliza bandas entre sensores diferentes | Landsat 5 (B1-B5,B7) → Landsat 8/9 (B2-B7) → schema unificado |

**Bandas unificadas:** `blue`, `green`, `red`, `nir`, `swir1`, `swir2`

### 3. Calculo de Indices (15 Features)

O pipeline computa 15 features por pixel para alimentar o classificador:

| # | Feature | Formula | Detecta |
|---|---------|---------|---------|
| 1 | Blue | Banda espectral | Assinatura espectral base |
| 2 | Green | Banda espectral | Assinatura espectral base |
| 3 | Red | Banda espectral | Assinatura espectral base |
| 4 | NIR | Banda espectral | Assinatura espectral base |
| 5 | **NDVI** | `(NIR - RED) / (NIR + RED)` | Vegetacao |
| 6 | **NDWI** | `(GREEN - NIR) / (GREEN + NIR)` | Agua |
| 7 | **NDBI** | `(SWIR1 - NIR) / (SWIR1 + NIR)` | Area construida |
| 8 | **SAVI** | `((NIR - RED) / (NIR + RED + L)) * (1 + L)` | Vegetacao em solo misto |
| 9 | **EVI** | `2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)` | Vegetacao densa |
| 10 | SWIR1 | Banda espectral | Umidade do solo/vegetacao |
| 11 | SWIR2 | Banda espectral | Minerais, solo exposto |
| 12 | **GLCM Contraste** | Matriz de co-ocorrencia (janela 5x5) | Diferencia floresta de gramado |
| 13 | **GLCM Homogeneidade** | Matriz de co-ocorrencia (janela 5x5) | Areas urbanas uniformes |
| 14 | **Elevacao** | SRTM 30m | Separa varzea de encosta |
| 15 | **Declividade** | Derivada do SRTM | Areas ingremes |

### 4. Classificacao por Ensemble ML

O sistema utiliza um **ensemble de 3 classificadores** com soft voting:

```
Feature Stack (15 features por pixel)
              │
┌─────────────┼─────────────┐
▼             ▼             ▼
Random Forest  XGBoost     SVM (RBF)
(500 arvores) (Gradient    (kernel)
              Boosting)
│             │             │
▼             ▼             ▼
Pred A       Pred B       Pred C
│             │             │
└─────────────┼─────────────┘
              ▼
    Soft Voting Ensemble
    (media ponderada por F1)
              │
              ▼
    Predicao final (5 classes)
```

**5 classes de uso do solo:**

| Codigo | Classe | Cor |
|--------|--------|-----|
| 1 | Floresta | Verde escuro |
| 2 | Vegetacao media | Verde claro |
| 3 | Urbano | Cinza |
| 4 | Solo exposto | Marrom |
| 5 | Agua | Azul |

**Pos-processamento espacial:**
- Filtro de moda (janela 3x3)
- Minimum Mapping Unit (MMU) — poligonos < 0.5 ha absorvidos pela classe vizinha
- Regras de consistencia hidrica

**Metas de validacao:**

| Validacao | Metodo | Metrica alvo |
|-----------|--------|-------------|
| Hold-out 70/30 | Split estratificado | F1 >= 0.85 por classe |
| K-Fold (k=5) | Cross-validation espacial | Kappa >= 0.80 |
| MapBiomas cross-check | Comparacao pixel a pixel | Agreement >= 75% |
| Consistencia temporal | Analise de transicoes | Remove flip-flops impossiveis |

### 5. Change Detection

- **Diferenca NDVI** entre anos consecutivos → mapa de perda/ganho
- **Matriz de transicao** de classes — "o que era → o que virou"
- **Quantificacao em hectares** por classe, bairro e ano
- **Deteccao de hotspots** — areas com maior perda acumulada
- Estatisticas agregadas por bairro e regional administrativa

### 6. Exportacao

| Formato | Conteudo | Uso |
|---------|----------|-----|
| **Cloud-Optimized GeoTIFF (COG)** | NDVI, classificacao, change detection | Tile serving sob demanda |
| **Parquet** | Estatisticas por bairro/ano | Consultas rapidas no backend |
| **SQLite** | Eventos historicos | CRUD de eventos |
| **PNG** | Mapas renderizados | Visualizacao rapida |

---

## API REST

O backend FastAPI expoe os seguintes endpoints:

### Health Check

```http
GET /api/health
```

```json
{ "status": "ok", "version": "2.0.0" }
```

### Tiles (Mapa)

```http
GET /api/tiles/{layer}/{year}/{z}/{x}/{y}.png
```

Serve tiles PNG do mapa a partir de COGs via rio-tiler.

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `layer` | string | `ndvi`, `classification`, `change` |
| `year` | int | Ano (2000-2024) |
| `z`, `x`, `y` | int | Coordenadas de tile XYZ |

### Imagem Completa

```http
GET /api/{layer}/{year}/image?width=800&height=1024&classes=all
```

Retorna imagem PNG da camada completa. O parametro `classes` permite filtrar classes especificas na classificacao.

### Consulta Pontual NDVI

```http
GET /api/ndvi/{year}/point?lat=-25.43&lon=-49.27
```

```json
{ "year": 2023, "lat": -25.43, "lon": -49.27, "ndvi": 0.72 }
```

### Estatisticas Anuais

```http
GET /api/stats/yearly
```

Retorna series temporais de NDVI medio, area verde (ha) e distribuicao de classes para todos os anos.

### Estatisticas por Bairro

```http
GET /api/stats/bairro/{name}/{year}
```

Exemplo:

```http
GET /api/stats/bairro/Centro/2023
```

### Estatisticas de Area Customizada

```http
POST /api/stats/area
Content-Type: application/json

{
  "geojson": { "type": "Polygon", "coordinates": [[...]] },
  "year": 2023
}
```

### Eventos

```http
# Listar eventos (com filtros opcionais)
GET /api/events?year=2015&category=parque_area_verde&bairro=Centro&limit=500

# Criar evento
POST /api/events
Content-Type: application/json
{
  "data": "2015-06-01",
  "titulo": "Inauguracao do Parque Linear",
  "categoria": "parque_area_verde",
  "impacto_ndvi": "positivo"
}

# Listar categorias
GET /api/events/categories

# Estatisticas de eventos por ano e categoria
GET /api/events/stats
```

### Bairros e Anos Disponiveis

```http
GET /api/bairros      # GeoJSON com limites dos bairros
GET /api/years        # Lista de anos com dados disponiveis
```

---

## Stack Tecnologica

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| **Linguagem** | Python | 3.10+ |
| **Backend API** | FastAPI | 2.0 |
| **Frontend** | React + TypeScript | 18.3 |
| **Mapa interativo** | MapLibre GL + react-map-gl | 4.0 / 7.1 |
| **Estilizacao** | Tailwind CSS | 4.0 |
| **Graficos** | Recharts | 2.12 |
| **Animacoes** | Framer Motion | 11.0 |
| **Icones** | Lucide React | 0.400 |
| **Bundler** | Vite | 6.0 |
| **Geoprocessamento** | rasterio, geopandas, shapely, pyproj | - |
| **Tile serving** | rio-tiler (COGs sob demanda) | 6.0+ |
| **Indices espectrais** | NumPy, scikit-image (GLCM) | - |
| **ML Ensemble** | scikit-learn (RF, SVM) + XGBoost | - |
| **Earth Engine** | earthengine-api | 0.1.380+ |
| **Dados tabulares** | pandas, pyarrow (Parquet) | - |
| **Banco de dados** | SQLite3 | - |
| **Exportacao COG** | rio-cogeo | 5.0+ |
| **Testes** | pytest | 7.4+ |
| **Containers** | Docker + Docker Compose | 3.8 |
| **Dashboard Streamlit** | Streamlit (app/) | 1.x |

---

## Como Executar

### Pre-requisitos

- Python 3.10+
- Node.js 18+
- Docker e Docker Compose (opcional)
- Credenciais do Google Earth Engine (apenas para rodar o pipeline de coleta)

### Modo Desenvolvimento

**Backend:**

```bash
cd CwbVerde
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

O backend estara disponivel em `http://localhost:8000`. Documentacao interativa (Swagger) em `http://localhost:8000/docs`.

**Frontend:**

```bash
cd CwbVerde/frontend
npm install
npm run dev
```

O frontend estara disponivel em `http://localhost:5173`.

**Pipeline (processamento de dados):**

```bash
# Rodar pipeline completo (todos os anos, 2000-2024)
python -m pipeline.run_pipeline

# Rodar para anos especificos
python -m pipeline.run_pipeline --years 2020 2021 2022 2023

# Rodar apenas etapas especificas
python -m pipeline.run_pipeline --steps preprocess features
```

**Seed de eventos:**

```bash
python seed_events.py
```

**Testes:**

```bash
pytest tests/ -v
```

### Docker

```bash
docker-compose up --build
```

| Servico | Porta | URL |
|---------|-------|-----|
| Backend (FastAPI) | 8000 | `http://localhost:8000` |
| Frontend (React) | 3000 | `http://localhost:3000` |

Os volumes `./data`, `./pipeline` e `./events` sao montados automaticamente no container do backend.

---

## Estrutura de Pastas

```
CwbVerde/
├── backend/                          # API FastAPI
│   ├── main.py                       # Entrypoint da API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── api/                          # Rotas (modular)
│   └── services/
│       ├── tile_service.py           # Serving de tiles via rio-tiler
│       ├── stats_service.py          # Estatisticas por bairro/area
│       └── events_service.py         # CRUD de eventos
│
├── frontend/                         # Dashboard React
│   ├── src/
│   │   ├── App.tsx                   # Roteamento principal
│   │   ├── main.tsx                  # Entrypoint
│   │   ├── components/               # Componentes reutilizaveis
│   │   ├── pages/                    # Paginas do dashboard
│   │   ├── hooks/                    # Custom hooks
│   │   ├── styles/                   # Estilos globais
│   │   └── utils/                    # Utilitarios
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vite.config.ts
│   └── package.json
│
├── pipeline/                         # ML e Visao Computacional
│   ├── config.py                     # Constantes, paths, bandas
│   ├── run_pipeline.py               # Orquestrador
│   ├── ingest/
│   │   ├── gee_collector.py          # Coleta via Google Earth Engine
│   │   ├── mapbiomas_loader.py       # Dados MapBiomas
│   │   └── shapefiles.py            # Geometria de Curitiba
│   ├── preprocess/
│   │   ├── cloud_mask.py             # Mascara de nuvens (QA_PIXEL)
│   │   ├── clip_reproject.py         # Recorte e reprojecao
│   │   └── harmonize.py             # Harmonizacao entre sensores
│   ├── features/
│   │   ├── indices.py                # NDVI, NDWI, NDBI, SAVI, EVI
│   │   ├── texture.py                # GLCM (contraste, homogeneidade)
│   │   └── terrain.py               # Elevacao e declividade (SRTM)
│   ├── classification/
│   │   ├── base.py                   # Classe abstrata BaseClassifier
│   │   ├── ensemble.py               # RF + XGBoost + SVM
│   │   ├── postprocess.py            # Filtro de moda, MMU
│   │   └── validation.py            # Metricas, cross-validation
│   ├── analysis/
│   │   ├── change_detection.py       # Perda/ganho de vegetacao
│   │   ├── statistics.py             # Agregacoes por bairro/ano
│   │   └── hotspots.py              # Areas criticas
│   └── export/
│       ├── cog_writer.py             # Cloud-Optimized GeoTIFF
│       └── parquet_writer.py         # Parquet para estatisticas
│
├── app/                              # Dashboard Streamlit (legado)
│   ├── Home.py
│   ├── pages/
│   │   ├── 1_Mapa_Interativo.py
│   │   ├── 2_Evolucao_Temporal.py
│   │   ├── 3_Analise_Bairros.py
│   │   ├── 4_Eventos_Historia.py
│   │   └── 5_Relatorios.py
│   ├── components/
│   ├── utils/
│   └── styles/
│
├── events/                           # Sistema de eventos historicos
│   ├── database.py                   # CRUD SQLite
│   ├── correlation.py                # Correlacao evento <-> NDVI
│   ├── scrapers/                     # Coleta automatizada
│   │   ├── diario_oficial.py
│   │   ├── mapbiomas_alertas.py
│   │   ├── ippuc_dados.py
│   │   └── ibge_censos.py
│   └── seed_data/
│       ├── marcos_iniciais.json
│       └── eventos_completos.json
│
├── data/                             # Dados geoespaciais (gitignored)
│   ├── raw/                          # Imagens brutas do GEE
│   ├── processed/                    # Imagens pre-processadas
│   ├── features/                     # Feature stacks (15 bandas)
│   ├── ndvi/                         # NDVI anual (COG)
│   ├── classification/               # Mapas de classificacao
│   ├── change/                       # Mapas de mudanca
│   ├── mapbiomas/                    # Dados MapBiomas
│   ├── shapefiles/                   # Limites de Curitiba/bairros
│   ├── stats/                        # Parquet com estatisticas
│   └── events.db                     # SQLite com eventos
│
├── models/                           # Modelos treinados (.joblib)
├── outputs/                          # Saidas do pipeline
│   ├── maps/                         # PNGs renderizados
│   ├── animations/                   # GIFs/videos temporais
│   ├── cog/                          # COGs otimizados
│   └── reports/                      # Relatorios gerados
│
├── tests/                            # Suite de testes (pytest)
│   ├── test_indices.py
│   ├── test_classification.py
│   ├── test_change_detection.py
│   ├── test_events_db.py
│   └── ...                           # 15+ arquivos de teste
│
├── notebooks/                        # Jupyter notebooks explorativos
├── gee_scripts/                      # Scripts JavaScript para GEE
├── docs/                             # Documentacao e specs
│
├── docker-compose.yml                # Orquestracao de containers
├── requirements.txt                  # Dependencias Python
├── pyproject.toml                    # Metadados do projeto
├── run_full_system.py                # Runner completo do sistema
├── seed_events.py                    # Seed de eventos no banco
└── README.md
```

---

## Fontes de Dados

| Fonte | Tipo | Periodo | Resolucao | Uso |
|-------|------|---------|-----------|-----|
| **Landsat 5 TM** (USGS) | Imagem satelite | 2000-2012 | 30m | Composicoes anuais |
| **Landsat 8 OLI** (USGS) | Imagem satelite | 2013-2020 | 30m | Composicoes anuais |
| **Landsat 9 OLI-2** (USGS) | Imagem satelite | 2021-2024 | 30m | Composicoes anuais |
| **Sentinel-2 MSI** (ESA) | Imagem satelite | 2017-2024 | 10m | Complemento multisensor |
| **MapBiomas** Col. 8 | Classificacao | 1985-2023 | 30m | Ground truth + cross-check |
| **PRODES** (INPE) | Desmatamento | Anual | 60m | Validacao |
| **SRTM** (NASA) | Elevacao | Estatico | 30m | Features (elevacao, declividade) |
| **IPPUC** | Shapefiles | Atual | Vetorial | Limites de bairros e regionais |
| **IBGE** | Censos/estimativas | Decenio | Tabular | Contexto demografico |

---

## Eventos Historicos

O sistema integra **1242 eventos historicos** de Curitiba que impactam (ou correlacionam-se com) a cobertura vegetal da cidade.

### Categorias

| Categoria | Exemplos | Impacto esperado no NDVI |
|-----------|----------|--------------------------|
| `legislacao` | Leis de zoneamento, plano diretor | Pode liberar ou proteger areas |
| `parque_area_verde` | Criacao de parques, bosques, RPPNMs | **Positivo** |
| `obra_infraestrutura` | Viadutos, contornos, metro | **Negativo** |
| `empreendimento` | Shopping centers, condominios | **Negativo** |
| `desastre_ambiental` | Enchentes, incendios | Perda pontual |
| `politica_publica` | IPTU Verde, Biocidade, arborizacao | **Positivo** |
| `licenciamento` | EIA/RIMA, licencas de supressao | Precede desmatamento |
| `educacao_cultura` | Universidades, centros culturais | Neutro/negativo |
| `transporte` | BRT, ciclovias, terminais | Misto |
| `demografico` | Censos, marcos populacionais | Contexto |

### Correlacao Evento <-> NDVI

O sistema calcula automaticamente o impacto de cada evento:

1. NDVI medio do bairro **1 ano antes** e **1 ano depois** do evento
2. **Delta NDVI** — se caiu > 0.05, impacto negativo confirmado
3. Heatmap de correlacao — quais categorias tem maior impacto real
4. Transforma a timeline em ferramenta analitica de causalidade

### Modelo de dados

```sql
eventos (
    id              INTEGER PRIMARY KEY,
    data            DATE NOT NULL,
    titulo          TEXT NOT NULL,
    descricao       TEXT,
    categoria       TEXT NOT NULL,
    subcategoria    TEXT,
    fonte           TEXT,
    url_fonte       TEXT,
    bairros         JSON,
    regional        TEXT,
    coordenadas     JSON,
    impacto_ndvi    TEXT,           -- "negativo" / "positivo" / "neutro"
    relevancia      INTEGER DEFAULT 1,  -- 1-5
    criado_por      TEXT DEFAULT 'sistema',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## Estimativa de Volume de Dados

Curitiba = ~435 km2 = ~483.000 pixels a 30m.

| Camada | Por ano | 25 anos | Formato |
|--------|---------|---------|---------|
| Composicao multiespectral | ~8 MB | ~200 MB | COG (4 bandas, int16) |
| Feature stack (15 bandas) | ~30 MB | ~750 MB | COG (float32) |
| NDVI | ~2 MB | ~50 MB | COG (float32, 1 banda) |
| Classificacao | ~0.5 MB | ~12 MB | COG (uint8, 1 banda) |
| Change detection | ~0.5 MB | ~12 MB | COG (uint8) |
| **Total estimado** | | **~1 GB** | |

---

## Licenca

Este projeto esta licenciado sob a [MIT License](LICENSE).

---

## Autores

**Samuel Mauli** — Trabalho de Processamento de Imagens e Sensoriamento Remoto

---

<p align="center">
  <sub>Feito com dados abertos do Google Earth Engine, MapBiomas, IPPUC e IBGE.</sub>
</p>
