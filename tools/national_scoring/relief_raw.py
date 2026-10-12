"""Uncapped 750 m relief (the value c_relief = clip(relief/100) was cut from), at chunk midpoints.
Usage: relief_raw.py <processed_dir> <reg_dir>"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, rasterio
d, reg = Path(sys.argv[1]), Path(sys.argv[2])
ch = pd.read_parquet(reg / "chunks.parquet", columns=["x3857", "y3857"])
with rasterio.open(d / "relief.tif") as s:
    v = np.fromiter((x[0] for x in s.sample(np.column_stack([ch.x3857.values, ch.y3857.values]))), float, count=len(ch))
pd.DataFrame({"relief750": np.nan_to_num(v, nan=0.0)}).to_parquet(reg / "relief750.parquet")
print(pd.Series(v).describe().round(1).to_string())
