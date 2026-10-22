# Scenery additions: the reproduction check

`check.py` compares two pipeline builds of one region, scored without and with the
additions V, S2 and L, against the study's offline features in `tools/scenery_types/`.
[`docs/national-scenery-additions.md`](../../docs/national-scenery-additions.md) §3–4
describes how the two scratch builds were made and what they gave.

```
NS_WORK=<the scenery-types scratch dir> SUNDAYDRIVE_MAIN=<main checkout> \
  python check.py ne|ut <e1_processed> <full_processed> <results_dir>
```

`results/` holds the aggregate output (`ne_check.csv`, `ut_check.csv`). No row locates a mark.
