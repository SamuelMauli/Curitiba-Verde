"""Write statistics to Parquet files."""
from pathlib import Path

import pandas as pd


def write_stats_parquet(
    df: pd.DataFrame,
    output_path: str,
) -> None:
    """Write a DataFrame to Parquet with compression.

    Args:
        df: DataFrame with statistics.
        output_path: Path for output .parquet file.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, engine="pyarrow", compression="snappy")


def read_stats_parquet(path: str) -> pd.DataFrame:
    """Read statistics from a Parquet file."""
    return pd.read_parquet(path, engine="pyarrow")
