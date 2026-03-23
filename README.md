# CwbVerde — Mapeamento de Desmatamento de Curitiba

Sistema de visão computacional e sensoriamento remoto para mapear a evolução do desmatamento e cobertura vegetal de Curitiba-PR (2000–2024).

## Funcionalidades

- **NDVI Anual** — Cálculo de índice de vegetação para 25 anos (2000-2024) usando Landsat 5/8/9
- **Classificação ML** — Ensemble de 3 modelos (Random Forest + XGBoost + SVM) com 15 features espectrais/texturais/topográficas
- **5 Classes de Uso do Solo** — Floresta, Vegetação média, Urbano, Solo exposto, Água
- **Change Detection** — Detecção de perda/ganho de vegetação entre anos consecutivos
- **MapBiomas Integration** — Cross-validação com dados oficiais MapBiomas (2000-2023)
- **Timeline Histórica** — 3000+ eventos urbanos de Curitiba correlacionados com mudanças no NDVI
- **Dashboard Interativo** — 6 páginas Streamlit com mapas, gráficos e relatórios
- **Mapa Interativo** — Desenho de polígonos, seleção de bairros, comparação lado a lado
- **Relatórios** — Exportação em PDF, PNG e CSV

## Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| Pipeline | Python 3.10+, Google Earth Engine, rasterio, geopandas |
| ML | scikit-learn, XGBoost, scikit-image (GLCM) |
| Índices | NDVI, NDWI, NDBI, SAVI, EVI + Textura GLCM + SRTM |
| Dashboard | Streamlit, Plotly, Folium |
| Banco de Dados | SQLite (eventos, áreas, comparações) |
| Deploy | Hugging Face Spaces |

## Estrutura do Projeto

```
CwbVerde/
├── pipeline/                  # Pipeline de processamento
│   ├── config.py             # Configurações, bandas, CRS
│   ├── ingest/               # Coleta: GEE, MapBiomas, shapefiles
│   ├── preprocess/           # Cloud mask, clip, reproject, harmonize
│   ├── features/             # NDVI, NDWI, NDBI, SAVI, EVI, GLCM, terrain
│   ├── classification/       # Ensemble ML, pós-processamento, validação
│   ├── analysis/             # Change detection, estatísticas, hotspots
│   ├── export/               # COG writer, Parquet writer
│   └── run_pipeline.py       # Orquestrador
├── events/                    # Sistema de eventos históricos
│   ├── database.py           # SQLite CRUD
│   ├── correlation.py        # Correlação evento ↔ NDVI
│   ├── scrapers/             # Scrapers para dados públicos
│   └── seed_data/            # 15 marcos iniciais curados
├── app/                       # Dashboard Streamlit
│   ├── Home.py               # Visão geral com cards e gráficos
│   ├── pages/                # 5 páginas do dashboard
│   ├── utils/                # Data loaders, charts, map utils
│   └── styles/               # CSS customizado
├── tests/                     # 93+ testes (pytest)
├── data/                      # Dados processados (gitignored)
├── docs/                      # Specs e planos de implementação
└── requirements.txt
```

## Instalação

```bash
# Clone
git clone https://github.com/SamuelMauli/Curitiba-Verde.git
cd Curitiba-Verde

# Ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Dependências
pip install -r requirements.txt

# Verificar instalação
pytest tests/ -v
```

## Pipeline de Processamento

### 1. Coleta de Dados (Google Earth Engine)

```bash
# Requer conta GEE com service account
python -m pipeline.run_pipeline --steps ingest
```

### 2. Pré-processamento + NDVI + Features

```bash
python -m pipeline.run_pipeline --steps preprocess features
```

### 3. Classificação + Change Detection

```bash
python -m pipeline.run_pipeline --steps classify detect
```

## Dashboard

```bash
streamlit run app/Home.py
```

Acesse `http://localhost:8501` para ver:

| Página | Descrição |
|--------|-----------|
| Home | Cards resumo + gráficos de tendência |
| Mapa Interativo | Mapa com layers NDVI/classificação + desenho de polígonos |
| Evolução Temporal | Série temporal NDVI + timeline de eventos |
| Análise por Bairros | Ranking + mapa coroplético |
| Eventos e História | Timeline de 3000+ marcos + CRUD |
| Relatórios | Geração de PNG/CSV por área |

## Classificação ML

O sistema usa um **ensemble de 3 classificadores** com soft voting:

```
Feature Stack (15 features) → RF + XGBoost + SVM → Soft Voting → 5 classes
```

### Features (15)
1-6: Bandas espectrais (Blue, Green, Red, NIR, SWIR1, SWIR2)
7-11: Índices (NDVI, NDWI, NDBI, SAVI, EVI)
12-13: Textura GLCM (Contraste, Homogeneidade)
14-15: Terreno (Elevação SRTM, Declividade)

### Validação
- Hold-out 70/30 com split estratificado
- K-Fold espacial (k=5) com blocos geográficos de 1km²
- Cross-check pixel a pixel contra MapBiomas
- Correção de consistência temporal (sem flip-flops)

## Testes

```bash
# Todos os testes
pytest tests/ -v

# Apenas índices
pytest tests/test_indices.py -v

# Apenas classificação
pytest tests/test_classification.py -v
```

## Fontes de Dados

| Fonte | Uso |
|-------|-----|
| Landsat 5/8/9 (GEE) | Imagens multiespectrais 2000-2024 |
| Sentinel-2 (GEE) | Alta resolução 2015+ (futuro) |
| MapBiomas Col. 8 | Classificação de referência 2000-2023 |
| SRTM (GEE) | Modelo digital de elevação |
| IPPUC | Shapefile de bairros de Curitiba |
| Diário Oficial CWB | Legislação e licenciamentos |
| IBGE SIDRA | Dados censitários |

## Licença

MIT

## Autor

Trabalho Final — Processamento de Imagens e Sensoriamento Remoto (2024)
