"""Q4's decision rule, applied to q4_frontier.csv.

A policy qualifies at a bar if it keeps at least that share of P0's
seasonal-road scenery in every sample (us, near, ne, named). Among those, the
lowest expected stranded minutes per 1,000 trips in the seasonal-country
sample (`near`) wins: it is where the risk is, with 97 of its 220 trips on a
seasonal road, against 9 of 273 in the random US sample. Ties within 20% go
to the policy with no new app UI (no P5).

  python q4_choose.py [_pooled]  ->  q4_choice.csv (q4_choice_pooled.csv)
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SAMPLES = ["us", "near", "ne", "named"]


def main():
    import sys
    suffix = sys.argv[1] if len(sys.argv) > 1 else ""
    f = pd.read_csv(HERE / f"q4_frontier{suffix}.csv")
    s = f.pivot_table(index="policy", columns="sample", values="stranded_min_per_1000")[SAMPLES]
    k = f.pivot_table(index="policy", columns="sample", values="seasonal_scenery_kept")[SAMPLES]
    rows = []
    for bar in (0.80, 0.90, 0.95):
        ok = k[(k >= bar).all(axis=1)].index
        for p5 in (False, True):
            cand = [p for p in ok if p.endswith("+ P5") == p5]
            best = s.loc[cand].sort_values("near").head(5)
            for rank, (p, r) in enumerate(best.iterrows(), 1):
                rows.append(dict(bar=bar, p5=p5, rank=rank, policy=p,
                                 **{f"stranded_{x}": r[x] for x in SAMPLES},
                                 **{f"kept_{x}": k.loc[p, x] for x in SAMPLES}))
    out = pd.DataFrame(rows)
    out.to_csv(HERE / f"q4_choice{suffix}.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 80)
    print(out[out["rank"] <= 2].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
