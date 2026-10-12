"""Paired drive-cluster bootstrap of each candidate's mark separation minus the shipped score's."""
import sys, pickle
import numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from core import *  # noqa
with open(SP / "cands.pkl", "rb") as f:
    CAND = pickle.load(f)
D = load_marks(); y = D.y.to_numpy(); drives = D.drive.to_numpy(); u = np.unique(drives)
rng = np.random.default_rng(20261012)
ship = mark_values(D, CAND["S0 shipped"]["ne"])
picks = [rng.choice(u, len(u)) for _ in range(4000)]
idx = [np.concatenate([np.flatnonzero(drives == d) for d in p]) for p in picks]
rows = []
for name, by in CAND.items():
    s = mark_values(D, by["ne"])
    for sub, m in (("all", np.ones(len(D), bool)), ("Oct", (D.batch == "Oct").to_numpy()), ("Aug", (D.batch == "Aug").to_numpy())):
        diffs = []
        for ix in idx:
            ix = ix[m[ix]]
            if y[ix].all() or (~y[ix]).all():
                continue
            diffs.append(auc(y[ix], s[ix]) - auc(y[ix], ship[ix]))
        diffs = np.array(diffs)
        rows.append(dict(name=name, subset=sub, auc=auc(y[m], s[m]), diff=auc(y[m], s[m]) - auc(y[m], ship[m]),
                         lo=np.percentile(diffs, 5), hi=np.percentile(diffs, 95), p_worse=(diffs < 0).mean()))
T = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(T.pivot_table(index="name", columns="subset", values=["diff", "lo", "hi"], sort=False).round(3).to_string())
T.to_csv(sys.argv[1], index=False)
