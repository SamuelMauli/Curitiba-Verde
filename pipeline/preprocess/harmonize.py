"""Sensor harmonization — normalize band values across Landsat 5/8/9."""
import numpy as np
import rasterio


# Landsat Collection 2 Level-2 Surface Reflectance scaling factors
_SCALING = {
    "landsat5": {"scale": 0.0000275, "offset": -0.2},
    "landsat8": {"scale": 0.0000275, "offset": -0.2},
    "landsat9": {"scale": 0.0000275, "offset": -0.2},
    "sentinel2": {"scale": 0.0001, "offset": 0.0},
}


def get_scaling_coefficients(sensor: str) -> dict[str, float]:
    """Get scaling coefficients for a sensor.

    Args:
        sensor: One of "landsat5", "landsat8", "landsat9", "sentinel2".

    Returns:
        Dict with "scale" and "offset" keys.

    Raises:
        ValueError: If sensor is unknown.
    """
    if sensor not in _SCALING:
        raise ValueError(
            f"Unknown sensor: {sensor}. Expected one of {list(_SCALING.keys())}"
        )
    return _SCALING[sensor]


def harmonize_bands(
    input_path: str,
    output_path: str,
    sensor: str,
) -> None:
    """Apply scaling to convert raw DN to surface reflectance.

    Applies: reflectance = DN * scale + offset
    Output is float32 in approximate range [0, 1].

    Args:
        input_path: Path to raw GeoTIFF with 6 bands.
        output_path: Path for harmonized output.
        sensor: Sensor name for scaling lookup.
    """
    coeffs = get_scaling_coefficients(sensor)
    scale = coeffs["scale"]
    offset = coeffs["offset"]

    with rasterio.open(input_path) as src:
        meta = src.meta.copy()
        meta.update({"dtype": "float32"})
        data = src.read().astype(np.float32)

    # Apply scaling
    harmonized = data * scale + offset

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(harmonized)
