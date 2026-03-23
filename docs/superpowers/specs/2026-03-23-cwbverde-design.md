# CwbVerde — Design Specification

**Sistema de Mapeamento de Desmatamento e Planejamento Urbano de Curitiba**

Data: 2026-03-23
Status: Aprovado pelo usuário

---

## 1. Visão Geral

Sistema de visão computacional e sensoriamento remoto que mapeia a evolução do desmatamento e cobertura vegetal de Curitiba-PR de 2000 a 2024, combinando análise NDVI, classificação supervisionada por ensemble de ML, dados MapBiomas e uma timeline rica de eventos históricos urbanos.

### Público-alvo dual
- **Acadêmico:** Trabalho final de Processamento de Imagens e Sensoriamento Remoto
- **Planejamento público:** Protótipo de ferramenta de gestão urbana para secretarias municipais, ONGs e urbanistas

### Resultados esperados
- Mapas NDVI anuais (2000–2024) em GeoTIFF e PNG
- Mapas de classificação de uso do solo (5 classes) por ano
- Mapas de change detection (perda/ganho de vegetação)
- Dashboard interativo com seleção de área, comparação e timeline
- Relatórios exportáveis (PDF, CSV, GeoJSON)
- ~3000+ marcos históricos de Curitiba correlacionados com NDVI
- Deploy público em Hugging Face Spaces

---

## 2. Arquitetura Geral

O sistema se divide em 3 camadas:

### Camada 1: Pipeline de Processamento (offline)

Roda localmente ou no Google Colab. Processa imagens e gera dados consumíveis pelo dashboard.

```
GEE (Landsat/Sentinel) ──→ Pré-processamento ──→ NDVI anual (2000-2024)
                                                       │
MapBiomas (2000-2023) ──────────────────────────────────┤
                                                        ▼
                                                  Merge & Harmonização
                                                        │
                                        ┌───────────────┼───────────────┐
                                        ▼               ▼               ▼
                                  Ensemble ML      Change Detection   Estatísticas
                                  (RF+XGB+SVM)     (perda/ganho)      por bairro/ano
                                        │               │               │
                                        ▼               ▼               ▼
                                    COG TIFFs      COG TIFFs        Parquet/CSV
```

Saídas: Cloud-Optimized GeoTIFFs (carregam sob demanda) + Parquet para tabelas estatísticas.

### Camada 2: Backend de Dados (leve)

SQLite com 3 tabelas:
- `eventos` — timeline histórica (~3000+ marcos)
- `areas_customizadas` — polígonos salvos por usuários
- `comparacoes` — comparações salvas

### Camada 3: Dashboard Streamlit + Componente Custom

- Streamlit multipage — navegação, filtros, gráficos, estatísticas
- Componente React-Leaflet custom — mapa interativo com desenho de polígonos, seleção de bairros, split-screen para comparação
- Timeline interativa — slider + marcadores de eventos históricos clicáveis

### Fluxo de dados no dashboard

1. Usuário seleciona ano no slider
2. Streamlit carrega COG do ano → renderiza no mapa (tile on-demand)
3. Usuário desenha polígono OU clica bairro
4. Componente React envia GeoJSON ao Streamlit
5. Python recorta COG pela geometria → calcula stats da área
6. Exibe: NDVI médio, área verde (ha), classe dominante, gráfico temporal
7. Usuário pode adicionar 2ª área → comparação split-screen

---

## 3. Pipeline de ML e Visão Computacional

### Módulo 1: Coleta e Ingestão

- **Google Earth Engine** via service account — composições anuais Landsat 5/8/9 e Sentinel-2 (2000–2024)
- **MapBiomas Coleção 8** — classificação anual pronta (1985–2023), ~30 classes
- **Harmonização de sensores** — Landsat 5 (bandas 3,4) vs Landsat 8/9 (bandas 4,5) vs Sentinel-2 (bandas 4,8) normalizados para schema único
- Saída: 25 composições multiespectrais anuais + 24 rasters MapBiomas

### Módulo 2: Pré-processamento

- Correção atmosférica (Surface Reflectance Level-2 do GEE)
- Máscara de nuvens (QA_PIXEL band)
- Recorte pelo shapefile de Curitiba (IPPUC)
- Reprojeção para SIRGAS 2000 UTM 22S (EPSG:31982)
- Normalização radiométrica entre sensores
- Saída: 25 imagens limpas, recortadas, mesmo CRS

### Módulo 3: Índices e Features (15 features)

| # | Feature | Fórmula | Detecta |
|---|---------|---------|---------|
| 1-4 | Bandas espectrais | Blue, Green, Red, NIR | Assinatura espectral base |
| 5 | NDVI | (NIR-RED)/(NIR+RED) | Vegetação |
| 6 | NDWI | (GREEN-NIR)/(GREEN+NIR) | Água |
| 7 | NDBI | (SWIR-NIR)/(SWIR+NIR) | Área construída |
| 8 | SAVI | ((NIR-RED)/(NIR+RED+L))×(1+L) | Vegetação em solo misto |
| 9 | EVI | 2.5×(NIR-RED)/(NIR+6×RED-7.5×BLUE+1) | Vegetação densa |
| 10 | SWIR1 | Banda SWIR1 | Umidade solo/vegetação |
| 11 | SWIR2 | Banda SWIR2 | Minerais, solo exposto |
| 12 | Textura GLCM | Contraste (janela 5×5) | Diferencia floresta de gramado |
| 13 | Textura GLCM | Homogeneidade (janela 5×5) | Áreas urbanas uniformes |
| 14 | Elevação | SRTM 30m | Separa várzea de encosta |
| 15 | Declividade | Derivada do SRTM | Áreas íngremes |

Saída: 25 rasters de features (15 bandas cada) + 25 rasters NDVI individuais

### Módulo 4: Classificação Robusta (Ensemble 3 Camadas)

#### Camada 1: Ensemble de 3 Classificadores

```
Feature Stack (15 features por pixel)
              │
┌─────────────┼─────────────┐
▼             ▼             ▼
Random Forest  XGBoost     SVM (RBF)
(500 árvores) (Gradient    (kernel)
              Boosting)
│             │             │
▼             ▼             ▼
Pred A       Pred B       Pred C
│             │             │
└─────────────┼─────────────┘
              ▼
    Soft Voting Ensemble
    (média ponderada por F1)
              │
              ▼
    Predição final (5 classes)
```

5 classes: Floresta, Vegetação média, Urbano, Solo exposto, Água

#### Camada 2: Pós-processamento Espacial

- Filtro de moda (janela 3×3) — pixel assume classe mais frequente dos vizinhos
- Minimum Mapping Unit (MMU) — polígonos < 0.5 ha absorvidos pela classe vizinha
- Regras de consistência hídrica — pixels "água" devem estar próximos de corpos d'água conhecidos

#### Camada 3: Validação Multi-Nível

| Validação | Como | Métrica alvo |
|-----------|------|-------------|
| Hold-out 70/30 | Split estratificado | F1 >= 0.85 por classe |
| K-Fold (k=5) | Cross-validation espacial | Kappa >= 0.80 |
| MapBiomas cross-check | Compara pixel a pixel | Agreement >= 75% |
| Matriz de confusão | Análise de erros sistemáticos | Identifica classes fracas |
| Consistência temporal | Classe não pode flip-flop | Remove transições impossíveis |

#### Slot U-Net (Futuro)

```python
class BaseClassifier(ABC):
    @abstractmethod
    def train(self, X, y) -> None: ...
    @abstractmethod
    def predict(self, tile: np.ndarray) -> np.ndarray: ...
    @abstractmethod
    def evaluate(self, X_test, y_test) -> dict: ...

class EnsembleClassifier(BaseClassifier):  # Atual
class UNetClassifier(BaseClassifier):       # Futuro
class HybridClassifier(BaseClassifier):     # Futuro (Ensemble + U-Net voting)
```

U-Net treinará com patches 256x256, labels do MapBiomas, deploy no HF Spaces com GPU T4.

### Módulo 5: Change Detection e Análise

- Diferença NDVI entre anos consecutivos → mapa de perda/ganho
- Transição de classes — matriz "o que era → o que virou"
- Quantificação em hectares por classe, bairro, ano
- Detecção de hotspots — áreas com maior perda acumulada
- Estatísticas agregadas por bairro e regional administrativa
- Saída: 24 rasters de change detection + Parquet com estatísticas

### Orquestração

```python
run_pipeline(years, aoi, config)
    ├── 1. ingest(years)           → raw GeoTIFFs
    ├── 2. preprocess(raw)         → clean GeoTIFFs
    ├── 3. compute_features(clean) → feature stacks (15 bandas)
    ├── 4. classify(features)      → class maps (ensemble)
    ├── 5. change_detect(ndvi)     → change maps
    ├── 6. aggregate_stats(...)    → Parquet dataframes
    └── 7. export_cog(all)         → COG TIFFs
```

Cada módulo é independente e re-executável. Logs detalhados, cache de resultados intermediários.

---

## 4. Sistema de Eventos e Timeline Histórica

### Modelo de dados (SQLite)

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
    impacto_ndvi    TEXT,        -- "negativo" / "positivo" / "neutro"
    relevancia      INTEGER DEFAULT 1,  -- 1-5
    criado_por      TEXT DEFAULT 'sistema',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Categorias

| Categoria | Exemplos | Impacto esperado |
|-----------|----------|-----------------|
| legislacao | Leis de zoneamento, plano diretor | Pode liberar ou proteger áreas |
| parque_area_verde | Criação de parques, bosques, RPPNMs | Positivo |
| obra_infraestrutura | Viadutos, contornos, metrô | Negativo |
| empreendimento | Shopping centers, condomínios | Negativo |
| desastre_ambiental | Enchentes, incêndios | Perda pontual |
| politica_publica | IPTU Verde, Biocidade, arborização | Positivo |
| licenciamento | EIA/RIMA, licenças de supressão | Precede desmatamento |
| educacao_cultura | Universidades, centros culturais | Neutro/negativo |
| transporte | BRT, ciclovias, terminais | Misto |
| demografico | Censos, marcos populacionais | Contexto |

### Estratégia de coleta (~3000+ eventos)

**Fase 1 (automática):**
- Legislação municipal (scraping Diário Oficial) → ~800 eventos
- MapBiomas Alertas (API) → ~500 eventos
- IPPUC dados abertos → ~300 eventos
- IBGE censos/estimativas (API SIDRA) → ~50 eventos

**Fase 2 (curadoria semi-automática):**
- Notícias Gazeta do Povo/Plural → ~800 eventos
- Relatórios anuais SMMA → ~300 eventos
- Licenciamentos IAT → ~250 eventos

**Fase 3 (CRUD no dashboard):**
- Gestores urbanos adicionam eventos futuros

### Correlação Evento <-> NDVI

- NDVI médio do bairro 1 ano antes e 1 ano depois do evento
- Delta NDVI — se caiu > 0.05 → impacto negativo confirmado
- Heatmap de correlação — quais categorias têm maior impacto real
- Transforma timeline em ferramenta analítica de causalidade

---

## 5. Componente de Mapa Interativo (React-Leaflet Custom)

### Estrutura

```
streamlit_map_component/
├── frontend/
│   ├── src/
│   │   ├── MapComponent.tsx
│   │   ├── layers/
│   │   │   ├── NDVILayer.tsx
│   │   │   ├── ClassificationLayer.tsx
│   │   │   ├── ChangeDetectionLayer.tsx
│   │   │   └── BairrosLayer.tsx
│   │   ├── tools/
│   │   │   ├── PolygonDraw.tsx
│   │   │   ├── BairroSelect.tsx
│   │   │   └── CompareMode.tsx
│   │   ├── widgets/
│   │   │   ├── TimeSlider.tsx
│   │   │   ├── AreaPopup.tsx
│   │   │   ├── Legend.tsx
│   │   │   └── MiniChart.tsx
│   │   └── utils/
│   │       ├── cogLoader.ts
│   │       └── geoUtils.ts
│   ├── package.json
│   └── tsconfig.json
└── __init__.py
```

### Comunicação Streamlit <-> React

- **Streamlit → React (args):** ano selecionado, camada ativa, GeoJSON bairros, eventos do ano, URL do COG tile
- **React → Streamlit (value):** área desenhada (GeoJSON), bairro selecionado, viewport bounds, tipo de interação

### Modo Comparação (Split-Screen)

Tela divide em dois mapas independentes, cada um com:
- Seletor de área (bairro ou polígono)
- Slider temporal independente
- Seletor de camada

Painel inferior mostra comparação:
- NDVI médio, área verde (ha), classe dominante, variação vs 2000
- Gráfico temporal comparado
- Botão para exportar relatório comparativo

### Combinações de comparação suportadas

| Área A | Área B |
|--------|--------|
| Bairro | Bairro |
| Bairro | Polígono customizado |
| Polígono | Polígono |
| Bairro | Curitiba inteira (média) |
| Polígono | Média da regional |

### Interações

| Ação | Resultado |
|------|-----------|
| Scroll slider temporal | Mapa atualiza, COG carrega sob demanda |
| Clique em bairro | Borda destaca, popup com stats |
| Desenha polígono | Calcula stats em tempo real |
| Clique marcador de evento | Popup + zoom para região |
| Botão "Comparar" | Split-screen |
| Hover sobre pixel | Tooltip: coordenada e nome do bairro (vetorial, leve) |
| Click sobre pixel | Consulta rio-tiler: NDVI, classe, stats (debounce 200ms) |

---

## 6. Páginas do Dashboard

### Página 1: "Visão Geral" (Home)
- Mapa com NDVI do ano mais recente (2024)
- Cards: área verde total (ha), % cobertura, variação vs 2000, bairro mais verde, bairro com maior perda
- Sparkline de tendência 2000→2024
- Link para mapa interativo

### Página 2: "Mapa Interativo"
- Componente React-Leaflet full-screen
- Sidebar: slider temporal, seletor de camada, opacidade, toggle bairros
- Ferramentas: desenhar polígono, clicar bairro, comparar
- Popup com stats ao selecionar área
- Modo comparação split-screen

### Página 3: "Evolução Temporal"
- Gráfico Plotly de série temporal NDVI
- Timeline de eventos com marcadores clicáveis
- Filtro por bairro/regional
- Tabela de dados exportável (CSV)

### Página 4: "Análise por Bairros"
- Ranking ordenável (mais verde, maior perda, maior ganho)
- Mapa coroplético por métrica
- Ficha detalhada por bairro (gráfico, classes, eventos)
- Comparação entre 2-3 bairros sobrepostos

### Página 5: "Eventos e História"
- Timeline vertical com ~3000+ marcos
- Filtros: categoria, bairro, período
- CRUD: adicionar/editar/remover eventos
- Link "Ver no mapa" por evento

### Página 6: "Relatórios"
- Geração de PDF/PNG por área
- Templates: bairro, área customizada, geral Curitiba
- Exportação de dados brutos (CSV, GeoJSON)

---

## 7. Estrutura de Pastas

```
CwbVerde/
├── app/                              # Dashboard Streamlit
│   ├── Home.py
│   ├── pages/
│   │   ├── 1_Mapa_Interativo.py
│   │   ├── 2_Evolucao_Temporal.py
│   │   ├── 3_Analise_Bairros.py
│   │   ├── 4_Eventos_Historia.py
│   │   └── 5_Relatorios.py
│   ├── components/
│   │   └── streamlit_map/
│   │       ├── frontend/
│   │       └── __init__.py
│   ├── styles/
│   │   └── custom.css
│   └── config.py
├── pipeline/                         # ML e Visão Computacional
│   ├── config.py
│   ├── ingest/
│   │   ├── gee_collector.py
│   │   ├── mapbiomas_loader.py
│   │   └── shapefiles.py
│   ├── preprocess/
│   │   ├── cloud_mask.py
│   │   ├── clip_reproject.py
│   │   └── harmonize.py
│   ├── features/
│   │   ├── indices.py
│   │   ├── texture.py
│   │   └── terrain.py
│   ├── classification/
│   │   ├── base.py
│   │   ├── ensemble.py
│   │   ├── unet.py
│   │   ├── hybrid.py
│   │   ├── postprocess.py
│   │   └── validation.py
│   ├── analysis/
│   │   ├── change_detection.py
│   │   ├── statistics.py
│   │   └── hotspots.py
│   ├── export/
│   │   ├── cog_writer.py
│   │   └── parquet_writer.py
│   └── run_pipeline.py
├── events/
│   ├── database.py
│   ├── scrapers/
│   │   ├── diario_oficial.py
│   │   ├── mapbiomas_alertas.py
│   │   ├── ippuc_dados.py
│   │   └── ibge_censos.py
│   ├── correlation.py
│   └── seed_data/
│       └── marcos_iniciais.json
├── data/
│   ├── raw/
│   ├── processed/
│   ├── features/
│   ├── ndvi/
│   ├── classification/
│   ├── change/
│   ├── mapbiomas/
│   ├── shapefiles/
│   ├── stats/
│   └── events.db
├── models/
│   ├── ensemble_v1.joblib
│   └── training_report.json
├── outputs/
│   ├── maps/
│   ├── animations/
│   ├── reports/
│   └── cog/
├── notebooks/
│   ├── 01_exploracao_gee.ipynb
│   ├── 02_analise_ndvi.ipynb
│   ├── 03_treino_classificador.ipynb
│   └── 04_validacao_mapbiomas.ipynb
├── gee_scripts/
│   └── coleta_landsat.js
├── tests/
│   ├── test_indices.py
│   ├── test_classification.py
│   ├── test_change_detection.py
│   └── test_events_db.py
├── docs/
├── requirements.txt
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## 8. Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.10+ |
| Dashboard | Streamlit 1.x |
| Mapa custom | React 18 + Leaflet + TypeScript |
| Bridge | streamlit-component-lib |
| Geoprocessamento | rasterio, geopandas, shapely, pyproj |
| Tile serving | rio-tiler (leitura sob demanda de COGs) |
| Features | numpy, scikit-image (GLCM) |
| ML Ensemble | scikit-learn (RF, SVM) + xgboost |
| ML Futuro | PyTorch + segmentation-models-pytorch |
| Earth Engine | earthengine-api |
| Gráficos | plotly, matplotlib, seaborn |
| Banco de dados | SQLite3 |
| Exportação | reportlab (PDF), imageio (GIF) |
| Dados tabulares | pandas, pyarrow (Parquet) |
| Testes | pytest |
| Deploy | Hugging Face Spaces (Streamlit SDK) |
| GPU futuro | Hugging Face Spaces (GPU T4) |

---

## 9. Deploy

- **Plataforma:** Hugging Face Spaces (gratuito)
- **SDK:** Streamlit
- **GPU:** T4 gratuita (para inferência U-Net futura)
- **Dados pré-processados:** COG TIFFs + Parquet commitados no Space ou carregados via HF Datasets
- **SQLite:** persiste no Space (eventos + áreas)
- **Acesso:** URL pública, qualquer pessoa com o link acessa

---

## 10. Decisões de Design

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Framework dashboard | Streamlit + componente React custom | Velocidade Python + interatividade rica no mapa |
| Formato raster | Cloud-Optimized GeoTIFF (COG) | Carrega sob demanda, não estoura memória |
| Classificador | Ensemble (RF+XGB+SVM) | Mais robusto que modelo único |
| Dados de referência | MapBiomas + pipeline próprio | MapBiomas como ground truth, pipeline próprio para 2024 e demonstração técnica |
| Banco de dados | SQLite | Zero configuração, suficiente para o volume |
| Deploy | HF Spaces | Gratuito, GPU disponível, URL pública |
| Período temporal | Anual contínuo 2000-2024 | 25 snapshots para tendências graduais |
| Eventos | ~3000+ marcos históricos | Correlação causal com NDVI |
| Comparação | Qualquer área vs qualquer área | Máxima flexibilidade para gestores |
| Tile serving | rio-tiler via endpoint Streamlit | Serve COG tiles sob demanda sem tile server separado |
| Persistência | HF Datasets API para dados mutáveis | SQLite efêmero em HF Spaces, backup via HF Datasets |
| Autenticação CRUD | HF Spaces OAuth | Somente usuários autenticados podem criar/editar eventos |
| GEE runtime | Build-time only | Nenhuma credencial GEE no deploy — tudo pré-processado |
| GLCM | scikit-image | scipy não tem GLCM nativo |

---

## 11. Resolução de Riscos Arquiteturais

### CRITICAL 1: Tile Serving de COGs

O Streamlit não serve tiles XYZ nativamente. Solução: **rio-tiler** integrado no Python side.

- O pipeline exporta COGs otimizados (overviews internos, compressão deflate)
- No dashboard, `rio-tiler` lê o COG e extrai tiles/regions sob demanda via rasterio
- O componente React-Leaflet recebe imagens PNG base64 do Streamlit (via args), não URLs de tile server
- Para áreas grandes, usa-se overview do COG (resolução reduzida) e full-res só no zoom alto
- Alternativa de fallback: pré-renderizar PNGs por ano/camada durante o pipeline e servir como estáticos

```python
# Exemplo de integração rio-tiler no Streamlit
from rio_tiler.io import Reader

def get_tile_png(cog_path, bounds, width=512, height=512):
    with Reader(cog_path) as src:
        img = src.part(bounds, dst_crs="EPSG:4326", width=width, height=height)
        return img.render(img_format="PNG")
```

### CRITICAL 2: Persistência no HF Spaces

Containers HF Spaces são efêmeros — filesystem reseta em restarts. Solução em 2 camadas:

- **Dados imutáveis** (COGs, Parquet, shapefiles, seed events): commitados no repo do Space ou hospedados em HF Dataset separado, referenciados por URL
- **Dados mutáveis** (eventos criados por usuários, áreas customizadas, comparações): persistidos via **HF Datasets API** como dataset auxiliar `CwbVerde-userdata`
- SQLite usado apenas como cache local em runtime, reconstruído no boot a partir do HF Dataset
- Sync periódico: a cada write no CRUD, salva no HF Dataset via `huggingface_hub`

```python
# Estratégia de persistência
from huggingface_hub import HfApi

def sync_events_to_hub(db_path, repo_id="usuario/CwbVerde-userdata"):
    api = HfApi()
    api.upload_file(path_or_fileobj=db_path,
                    path_in_repo="events.db",
                    repo_id=repo_id, repo_type="dataset")
```

### CRITICAL 3: Autenticação para CRUD

URL é pública, mas operações de escrita precisam de controle. Solução:

- **HF Spaces OAuth** integrado ao Streamlit — usuários fazem login com conta Hugging Face
- **Leitura:** aberta para todos (qualquer visitante vê tudo)
- **Escrita (CRUD eventos, salvar áreas):** requer login HF
- **Admin:** token especial para bulk operations (seed data, scrapers)
- Streamlit `st.experimental_user` fornece info do usuário logado no HF Spaces

### IMPORTANT: Validação Degradada para 2024

MapBiomas cobre até 2023. Para 2024, sem ground truth de referência:

- Classificação 2024 usa o mesmo modelo treinado nos anos anteriores
- Cross-check: compara classificação 2023 do pipeline vs MapBiomas 2023 para medir confiança
- Dashboard exibe badge de confiança: "Validado (2000-2023)" vs "Estimado (2024)"
- Quando MapBiomas 2024 for lançado, re-validar automaticamente

### IMPORTANT: Estratégia de Training Labels

Fonte e coleta de amostras de treino para o ensemble:

- **Fonte primária:** MapBiomas reclassificado (30+ classes → 5 classes target)
- **Reclassificação:** Floresta Natural + Formação Florestal → Floresta; Pastagem + Campo → Vegetação média; Infraestrutura Urbana → Urbano; Solo Exposto + Mineração → Solo exposto; Rio + Lago → Água
- **Amostragem:** 500 pixels por classe, estratificado espacialmente em blocos de 1km² para evitar autocorrelação
- **Complemento manual:** ~50 amostras por classe coletadas no QGIS sobre Google Satellite para refinar bordas ambíguas
- **Split:** 70% treino / 30% teste, com spatial blocking (blocos inteiros no teste, nunca pixels vizinhos em treino e teste)

### IMPORTANT: Estimativa de Volume de Dados

Curitiba = ~435 km² = ~483.000 pixels a 30m.

| Camada | Por ano | 25 anos | Formato |
| --- | --- | --- | --- |
| Composição multiespectral | ~8 MB | ~200 MB | COG (4 bandas, int16) |
| Feature stack (15 bandas) | ~30 MB | ~750 MB | COG (float32) |
| NDVI | ~2 MB | ~50 MB | COG (float32, 1 banda) |
| Classificação | ~0.5 MB | ~12 MB | COG (uint8, 1 banda) |
| Change detection | ~0.5 MB | ~12 MB | COG (uint8) |
| MapBiomas | ~0.5 MB | ~12 MB | COG (uint8) |
| **Total estimado** | | **~1 GB** | |

Estratégia: hospedar rasters em HF Dataset `CwbVerde-data` (limite 50GB free) e referenciar no Space. Parquet de stats e SQLite de eventos ficam no repo do Space (~10 MB).

### IMPORTANT: Hover vs Click no Mapa

Tooltip de pixel-level em hover sobre COGs é inviável em performance. Solução:

- **Hover:** mostra apenas coordenada e nome do bairro (dados vetoriais, leves)
- **Click:** consulta pixel do COG via rio-tiler point query, retorna NDVI + classe + stats
- Debounce de 200ms no click para evitar queries excessivas

### IMPORTANT: Schemas SQLite Completos

```sql
areas_customizadas (
    id          INTEGER PRIMARY KEY,
    nome        TEXT,
    geojson     TEXT NOT NULL,
    criado_por  TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

comparacoes (
    id          INTEGER PRIMARY KEY,
    nome        TEXT,
    area_a_tipo TEXT NOT NULL,      -- 'bairro' | 'poligono' | 'regional' | 'cidade'
    area_a_ref  TEXT NOT NULL,      -- nome do bairro ou id da area_customizada
    area_b_tipo TEXT NOT NULL,
    area_b_ref  TEXT NOT NULL,
    ano_a       INTEGER,
    ano_b       INTEGER,
    camada      TEXT DEFAULT 'ndvi',
    criado_por  TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```
