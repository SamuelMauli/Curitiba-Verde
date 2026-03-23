"""Client for MapBiomas Alertas API — deforestation alerts."""


def fetch_alerts_curitiba(
    start_year: int = 2000,
    end_year: int = 2024,
) -> list[dict]:
    """Fetch deforestation alerts for Curitiba from MapBiomas Alertas.

    Returns list of dicts with data, titulo, coordenadas, area_ha.
    """
    # TODO: Implement MapBiomas Alertas API integration
    # API: https://alertas.mapbiomas.org/api
    # Filter by Curitiba municipality code (4106902)
    return []
