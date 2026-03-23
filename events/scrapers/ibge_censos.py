"""Client for IBGE SIDRA API — census and demographic data."""
import requests


def fetch_census_data() -> list[dict]:
    """Fetch census milestones for Curitiba from IBGE SIDRA.

    Returns list of demographic events (census years, population milestones).
    """
    # TODO: Implement IBGE SIDRA API calls
    # API: https://apisidra.ibge.gov.br/
    # Table 6579 (population by municipality)
    return []
