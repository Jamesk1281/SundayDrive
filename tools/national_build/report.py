"""The per-state and per-region tables docs/national-build.md reports.

Usage: report.py <config.json> <stitched_dir> <out_dir>

Writes per_state.csv (nodes, edges and km of the stitched graph by state, Texas's and
California's halves added together) and per_region_cost.csv (each region's ring PBF,
wall time and peak RSS per stage, and processed-directory disk before clean-up, from
build/<region>/stages.json), and prints both as markdown.

A node where two states' edges meet is counted in both states, so the state node
counts sum to more than the national total, which is printed alongside.
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regions  # noqa: E402
from build import load_config  # noqa: E402

def markdown(df: pd.DataFrame) -> str:
    """A markdown table, without pandas' optional tabulate dependency."""
    cols = list(df.columns)
    fmt = lambda v: f"{v:,}" if isinstance(v, (int,)) and not isinstance(v, bool) else str(v)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


STAGES = ["extract", "elevation", "terrain", "landcover", "protected", "score", "graph_part"]


def main(config: str, stitched: str, out_dir: str):
    c = load_config(config)
    s, out = Path(stitched), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    state_of = {r.name: r.state for r in regions.load(c["states"])}

    pr = pd.read_csv(s / "per_region.csv")
    pr["state"] = pr["region"].map(state_of)
    per_state = (pr.groupby("state")[["nodes", "edges", "km"]].sum()
                 .sort_values("km", ascending=False))
    per_state["km"] = per_state["km"].round(0).astype(int)
    per_state.to_csv(out / "per_state.csv")

    rows = []
    for name in pr["region"]:
        st = json.loads((Path(c["work"]) / name / "stages.json").read_text())
        row = {"region": name, "pbf_mb": round(st.get("pbf_gb", 0) * 1000),
               "disk_gb": st.get("disk_gb")}
        for k in STAGES:
            row[f"{k}_s"] = st.get(k, {}).get("wall_s")
        row["total_min"] = round(sum(st.get(k, {}).get("wall_s", 0) for k in STAGES) / 60, 1)
        row["peak_rss_gb"] = max(st.get(k, {}).get("peak_rss_gb") or 0 for k in STAGES)
        row["peak_stage"] = max(STAGES, key=lambda k: st.get(k, {}).get("peak_rss_gb") or 0)
        rows.append(row)
    cost = pd.DataFrame(rows)
    cost.to_csv(out / "per_region_cost.csv", index=False)

    report = json.loads((s / "stitch_report.json").read_text())
    print(markdown(per_state.reset_index()))
    print(f"\ntotal: {per_state['edges'].sum():,} edges, {per_state['km'].sum():,} km; "
          f"national nodes {report['graph']['nodes']:,} (state sums {per_state['nodes'].sum():,})\n")
    print(markdown(cost))
    print(f"\nprocess-hours {cost['total_min'].sum() / 60:.1f}, ring PBFs "
          f"{cost['pbf_mb'].sum() / 1000:.1f} GB, largest peak {cost['peak_rss_gb'].max()} GB "
          f"({cost.loc[cost['peak_rss_gb'].idxmax(), 'region']}, "
          f"{cost.loc[cost['peak_rss_gb'].idxmax(), 'peak_stage']}), "
          f"largest region disk {cost['disk_gb'].max()} GB")


if __name__ == "__main__":
    main(*sys.argv[1:4])
