"""Load and reclassify MapBiomas land cover data."""
import numpy as np
import rasterio

from pipeline.config import CLASS_NAMES


# MapBiomas Collection 8 → CwbVerde 5-class reclassification
# Full mapping: https://mapbiomas.org/codigos-de-legenda
_MAPBIOMAS_RECLASSIFICATION = {
    # Floresta (class 1)
    3: 1,   # Formação Florestal
    4: 1,   # Formação Savânica
    5: 1,   # Mangue
    6: 1,   # Floresta Alagável
    49: 1,  # Restinga Arborizada
    # Vegetação média (class 2)
    11: 2,  # Campo Alagado
    12: 2,  # Formação Campestre
    13: 2,  # Outra Formação não Florestal
    15: 2,  # Pastagem
    32: 2,  # Apicum
    29: 2,  # Afloramento Rochoso
    50: 2,  # Restinga Herbácea
    # Urbano (class 3)
    24: 3,  # Infraestrutura Urbana
    30: 3,  # Mineração
    # Solo exposto (class 4)
    25: 4,  # Outra Área não Vegetada
    23: 4,  # Praia, Duna e Areal
    20: 4,  # Cana
    39: 4,  # Soja
    40: 4,  # Arroz
    41: 4,  # Outras Lavouras Temporárias
    36: 4,  # Lavoura Perene
    46: 4,  # Café
    47: 4,  # Citrus
    35: 4,  # Dendê
    48: 4,  # Outras Lavouras Perenes
    9: 4,   # Silvicultura
    21: 4,  # Mosaico de Usos
    # Água (class 5)
    26: 5,  # Corpo D'Água Natural
    33: 5,  # Rio, Lago e Oceano
    31: 5,  # Aquicultura
    27: 5,  # Não observado → treat as nodata but map to 0
}


def reclassify_mapbiomas(
    input_path: str,
    output_path: str,
) -> None:
    """Reclassify MapBiomas raster from ~30 classes to 5 CwbVerde classes.

    Args:
        input_path: Path to MapBiomas GeoTIFF.
        output_path: Path for reclassified output.
    """
    with rasterio.open(input_path) as src:
        data = src.read(1)
        meta = src.meta.copy()

    reclassified = np.zeros_like(data, dtype=np.uint8)
    for mapbiomas_class, cwb_class in _MAPBIOMAS_RECLASSIFICATION.items():
        reclassified[data == mapbiomas_class] = cwb_class

    meta.update({"dtype": "uint8", "count": 1})
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(reclassified, 1)


def get_class_name(class_id: int) -> str:
    """Return human-readable class name."""
    return CLASS_NAMES.get(class_id, "Desconhecido")
