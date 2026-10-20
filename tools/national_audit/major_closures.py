"""Every closed_to_cars and seasonal_closures row on a motorway through
secondary road (or their links), by kind and tag: the list the next mis-tag
is in (docs/review-fixes-data.md, "What else closes a major road").

Usage: major_closures.py <processed_dir> [<rows.csv>]

Prints markdown: totals per table and kind, the tags, and the 30 longest
edges each table closes. With <rows.csv>, also writes every row found, with
its edge's highway, ref and name, for reading by hand.

An "edge" row closes its edge, so it has a length. A "through" row forbids
only driving through a node where two edges meet, so it is counted, not
measured. A row's km is its edge's length, each edge once.
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline"))
from common import FORD_OPEN_CLASSES  # noqa: E402

MAJOR = FORD_OPEN_CLASSES
LONGEST = 30


def seasonal_source(row) -> str:
    """Who closes a seasonal row: an OSM way, an OSM gate, or an agency's
    layer or hand table (winter_closures.py), named by its tag's first word."""
    first = row["tag"].split(" ", 1)[0]
    if first in ("mvum", "nps", "table"):
        return first
    return "osm gate" if row["node_id"] >= 0 else "osm way"


def family(tag: str, kind: str) -> str:
    """A tag cut to what groups like rows: the key of a conditional, not its
    dates; a park's code, not its description's wording."""
    if kind in ("mvum",):
        return "mvum " + tag.split(" ", 1)[1].split("=", 1)[0]
    if kind in ("nps", "table"):
        return tag.split(":", 1)[0]
    return re.sub(r"(:conditional)\s*=.*$", r"\1", tag)


def load(d: Path):
    edges = pd.read_parquet(d / "graph_edges.parquet", columns=["highway", "ref", "name"])
    closed = pd.read_parquet(d / "closed_to_cars.parquet")
    seasonal = pd.read_parquet(d / "seasonal_closures.parquet")
    out = {}
    for label, t in (("closed_to_cars", closed), ("seasonal_closures", seasonal)):
        t = t.drop(columns=[c for c in ("name", "ref") if c in t.columns])
        t = t.join(edges, on="edge")
        t = t[t["highway"].isin(MAJOR)].copy()
        if label == "seasonal_closures":
            t["kind"] = t.apply(seasonal_source, axis=1)
        t["family"] = [family(tag, k) for tag, k in zip(t["tag"], t["kind"])]
        out[label] = t
    return out


def km(t: pd.DataFrame) -> float:
    e = t[t["rule"] == "edge"].drop_duplicates("edge")
    return e["length_m"].sum() / 1000.0


def summary(label: str, t: pd.DataFrame) -> list[str]:
    lines = [f"### {label}", "",
             f"{len(t):,} rows on major roads: {t[t['rule'] == 'edge']['edge'].nunique():,} "
             f"edges closed ({km(t):,.1f} km) and {(t['rule'] == 'through').sum():,} "
             "through rows.", "",
             "| kind | rows | edges closed | km | through rows |", "|---|---:|---:|---:|---:|"]
    for kind, g in sorted(t.groupby("kind"), key=lambda kg: -km(kg[1])):
        lines.append(f"| {kind} | {len(g):,} | {g[g['rule'] == 'edge']['edge'].nunique():,} | "
                     f"{km(g):,.1f} | {(g['rule'] == 'through').sum():,} |")
    lines += ["", "| kind | tag | rows | km |", "|---|---|---:|---:|"]
    fam = [(k, f, g) for (k, f), g in t.groupby(["kind", "family"])]
    for kind, f, g in sorted(fam, key=lambda x: (-km(x[2]), -len(x[2]))):
        lines.append(f"| {kind} | `{f}` | {len(g):,} | {km(g):,.1f} |")
    lines += ["", f"The {LONGEST} longest edges closed:", "",
              "| edge | highway | ref | name | km | kind | tag |", "|---:|---|---|---|---:|---|---|"]
    top = (t[t["rule"] == "edge"].sort_values("length_m", ascending=False)
           .drop_duplicates("edge").head(LONGEST))
    for _, r in top.iterrows():
        tag = r["tag"] if len(r["tag"]) <= 70 else r["tag"][:67] + "..."
        lines.append(f"| {r['edge']} | {r['highway']} | {r['ref'] or ''} | {r['name'] or ''} | "
                     f"{r['length_m'] / 1000:.1f} | {r['kind']} | `{tag}` |")
    return lines + [""]


def main(d: str, rows_csv: str = None):
    tables = load(Path(d))
    for label, t in tables.items():
        print("\n".join(summary(label, t)))
    if rows_csv:
        pd.concat([t.assign(table=label) for label, t in tables.items()],
                  ignore_index=True).to_csv(rows_csv, index=False)


if __name__ == "__main__":
    main(*sys.argv[1:3])
