import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
# app/utils/report_generator.py
"""Generate PDF/PNG reports for areas."""
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import numpy as np


def generate_area_report_png(
    title: str,
    ndvi_array: np.ndarray,
    stats: dict,
    year: int,
) -> bytes:
    """Generate a PNG report image for an area.

    Returns PNG bytes.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # NDVI map
    ax = axes[0]
    im = ax.imshow(ndvi_array, cmap="RdYlGn", vmin=-0.2, vmax=0.8)
    ax.set_title(f"NDVI — {year}", fontsize=14, fontweight="bold")
    ax.axis("off")
    plt.colorbar(im, ax=ax, shrink=0.7, label="NDVI")

    # Stats text
    ax2 = axes[1]
    ax2.axis("off")
    text = f"""
    {title}
    Ano: {year}

    NDVI Médio: {stats.get('ndvi_mean', 'N/A'):.3f}
    Área Verde: {stats.get('green_area_ha', 'N/A'):.1f} ha
    Cobertura: {stats.get('green_percent', 'N/A'):.1f}%
    """
    ax2.text(0.1, 0.5, text, fontsize=14, verticalalignment="center",
             fontfamily="monospace", transform=ax2.transAxes)

    plt.suptitle(f"CwbVerde — Relatório de {title}", fontsize=16, fontweight="bold")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf.getvalue()
