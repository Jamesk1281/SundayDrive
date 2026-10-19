"""Flat storage for the router at US scale: strings, polylines and grids.

Today's router held the map as Python objects: 4.6 KB per node, about 88 GB
for the contiguous US (docs/usa-extension-feasibility.md §2). What it needs per
request is a corridor's worth of it. So everything here is a handful of numpy
arrays that a pack writes once (`router.Router.save_pack`) and the server maps
read-only. The kernel pages in the part a request touches and can drop it
again under pressure, so the bulk of the map is not memory the process holds
(docs/router-at-us-scale.md, "The pack").

Three shapes cover all of it:

  Strings   a dictionary-encoded string column: one int32 code per row, and
            the distinct values as one UTF-8 blob with offsets;
  Lines     polylines as int32 lon/lat in 1e-7 degrees, which is OSM's own
            precision, so the round trip to float64 is exact;
  Grid      items bucketed by the lon/lat cells they touch, for "what lies in
            this box" in time proportional to the answer, not to the map.
"""

import math

import numpy as np
import pyarrow as pa
import shapely

# OSM stores coordinates as integers of 1e-7 degrees, and pyosmium divides by
# exactly this, so lon * SCALE rounds back to the integer OSM had and dividing
# again gives the same float64 (checked on all 9,390,733 New England vertices).
SCALE = 10_000_000


class Strings:
    """A string column as codes into a table of distinct values.

    `codes[i]` is the row's value's index in the table, or -1 for a missing
    value. The table is one UTF-8 blob plus offsets, so it maps from disk like
    everything else rather than becoming millions of Python strings.
    """

    def __init__(self, codes, blob, offsets):
        self.codes, self.blob, self.offsets = codes, blob, offsets
        self._decoded = {}

    @classmethod
    def from_arrow(cls, column):
        """From a pyarrow string column."""
        encoded = pa.chunked_array(column).combine_chunks().dictionary_encode()
        values = encoded.dictionary.to_pylist()
        codes = encoded.indices.to_numpy(zero_copy_only=False)
        codes = np.where(np.isnan(codes), -1, codes).astype(np.int32) \
            if codes.dtype.kind == "f" else codes.astype(np.int32)
        return cls.from_values(codes, values)

    @classmethod
    def from_values(cls, codes, values):
        raw = [v.encode("utf-8") for v in values]
        offsets = np.zeros(len(raw) + 1, np.int64)
        np.cumsum([len(b) for b in raw], out=offsets[1:])
        blob = np.frombuffer(b"".join(raw), np.uint8) if raw else np.zeros(0, np.uint8)
        return cls(np.asarray(codes, np.int32), blob, offsets)

    def __len__(self):
        return len(self.codes)

    def text(self, code: int):
        """The value with this code, or None for -1."""
        if code < 0:
            return None
        hit = self._decoded.get(code)
        if hit is None:
            hit = bytes(self.blob[self.offsets[code]:self.offsets[code + 1]]).decode("utf-8")
            if len(self._decoded) < 200_000:
                self._decoded[code] = hit
        return hit

    def values(self, rows):
        """The values of `rows`, None where missing."""
        return [self.text(int(c)) for c in self.codes[np.asarray(rows)]]

    def all_values(self):
        """Every row's value, None where missing: for building a whole column
        on the small graphs the tests use, never on a request."""
        table = [self.text(c) for c in range(len(self.offsets) - 1)] + [None]
        return np.array(table, dtype=object)[self.codes]

    def arrays(self, name):
        return {f"{name}.codes": self.codes, f"{name}.blob": self.blob,
                f"{name}.offsets": self.offsets}

    @classmethod
    def load(cls, arrays, name):
        return cls(arrays[f"{name}.codes"], arrays[f"{name}.blob"],
                   arrays[f"{name}.offsets"])


class Coded:
    """A float64 column as small integer codes into a table of its distinct
    values: exact, and a quarter or an eighth of the size where the values
    repeat. The scenery components water, coast, farm and urban have under
    65,536 distinct values on the US graph, and the surface share has two.
    """

    def __init__(self, codes, values):
        self.codes, self.values = codes, values

    @classmethod
    def of(cls, column):
        values, codes = np.unique(np.asarray(column, np.float64), return_inverse=True)
        dtype = (np.uint8 if len(values) <= 256 else
                 np.uint16 if len(values) <= 65536 else np.int32)
        return cls(codes.ravel().astype(dtype), values)

    def __len__(self):
        return len(self.codes)

    def take(self, rows):
        return self.values[self.codes[rows]]

    def all(self):
        return self.values[self.codes]

    def arrays(self, name):
        return {f"{name}.codes": self.codes, f"{name}.values": self.values}

    @classmethod
    def load(cls, arrays, name):
        return cls(arrays[f"{name}.codes"], arrays[f"{name}.values"])


class Lines:
    """Polylines as int32 lon/lat (1e-7 degrees), one run of vertices per row.

    Geometry that is not on OSM's grid, which only a test's hand-made graph
    has, is kept as float64 degrees instead (`scale` 1), rather than moved.
    """

    def __init__(self, xy, start):
        self.xy, self.start = xy, start
        self.scale = SCALE if xy.dtype == np.int32 else 1.0

    @classmethod
    def from_wkb(cls, wkb, chunk=500_000):
        """From an array of WKB linestrings, a chunk at a time so that no more
        than `chunk` shapely objects ever exist at once."""
        parts, counts, exact = [], [], True
        for i in range(0, len(wkb), chunk):
            geoms = shapely.from_wkb(wkb[i:i + chunk])
            coords, index = shapely.get_coordinates(geoms, return_index=True)
            fixed = np.round(coords * SCALE)
            exact = exact and np.array_equal(fixed / SCALE, coords)
            parts.append(coords if not exact else fixed.astype(np.int32))
            counts.append(np.bincount(index, minlength=len(geoms)))
        if not exact:
            # Off the grid somewhere: keep every vertex as it came.
            parts = [p if p.dtype == np.float64 else p / SCALE for p in parts]
        xy = np.concatenate(parts) if parts else np.zeros((0, 2), np.int32)
        start = np.zeros(len(wkb) + 1, np.int64)
        if counts:
            np.cumsum(np.concatenate(counts), out=start[1:])
        return cls(xy, start)

    def __len__(self):
        return len(self.start) - 1

    def coords(self, row: int) -> np.ndarray:
        """One line's [lon, lat] vertices as float64."""
        return self.xy[self.start[row]:self.start[row + 1]] / self.scale

    def many(self, rows):
        """Vertices of several lines, concatenated, with the position in
        `rows` each came from: `shapely.get_coordinates(..., return_index=True)`."""
        rows = np.asarray(rows, np.int64)
        a, b = self.start[rows], self.start[rows + 1]
        idx = np.repeat(np.arange(len(rows)), b - a)
        take = _ranges(a, b)
        return self.xy[take] / self.scale, idx

    def bounds(self):
        """Per line (lon_min, lat_min, lon_max, lat_max), float64 degrees."""
        n = len(self)
        out = np.empty((n, 4))
        nonempty = self.start[1:] > self.start[:-1]
        at = self.start[:-1][nonempty]
        for k, (op, col) in enumerate(((np.minimum, 0), (np.minimum, 1),
                                       (np.maximum, 0), (np.maximum, 1))):
            v = op.reduceat(self.xy[:, col], at) if len(at) else np.zeros(0)
            out[nonempty, k] = v / self.scale
            out[~nonempty, k] = np.nan
        return out


class Grid:
    """Items bucketed by the lon/lat cells their boxes touch.

    `order[start[c]:start[c + 1]]` are the items in cell `c`, cells counted
    row by row from (`lon0`, `lat0`). An item whose box spans several cells
    is listed in each, so a query answers with `np.unique`.
    """

    def __init__(self, lon0, lat0, cell, ncols, nrows, order, start):
        self.lon0, self.lat0, self.cell = float(lon0), float(lat0), float(cell)
        self.ncols, self.nrows = int(ncols), int(nrows)
        self.order, self.start = order, start

    @classmethod
    def build(cls, boxes, cell):
        """`boxes` is (n, 4) lon_min, lat_min, lon_max, lat_max; NaN rows are
        left out."""
        ok = np.flatnonzero(np.isfinite(boxes).all(axis=1))
        if not len(ok):
            return cls(0.0, 0.0, cell, 1, 1, np.zeros(0, np.int32),
                       np.zeros(2, np.int64))
        b = boxes[ok]
        lon0 = math.floor(b[:, 0].min() / cell) * cell - cell
        lat0 = math.floor(b[:, 1].min() / cell) * cell - cell
        ncols = int(math.floor((b[:, 2].max() - lon0) / cell)) + 2
        nrows = int(math.floor((b[:, 3].max() - lat0) / cell)) + 2
        x0 = np.floor((b[:, 0] - lon0) / cell).astype(np.int64)
        y0 = np.floor((b[:, 1] - lat0) / cell).astype(np.int64)
        nx = np.floor((b[:, 2] - lon0) / cell).astype(np.int64) - x0 + 1
        ny = np.floor((b[:, 3] - lat0) / cell).astype(np.int64) - y0 + 1
        k = nx * ny
        item = np.repeat(ok, k)
        off = np.arange(int(k.sum())) - np.repeat(np.cumsum(k) - k, k)
        wide = np.repeat(nx, k)
        cells = ((np.repeat(y0, k) + off // wide) * ncols
                 + np.repeat(x0, k) + off % wide)
        order = np.argsort(cells, kind="stable")
        start = np.searchsorted(cells[order], np.arange(ncols * nrows + 1))
        return cls(lon0, lat0, cell, ncols, nrows,
                   item[order].astype(np.int32), start.astype(np.int64))

    def box(self, lon_min, lat_min, lon_max, lat_max, unique=True):
        """Items listed in any cell the box touches: a superset of the items
        whose own box meets it."""
        x0 = max(0, int(math.floor((lon_min - self.lon0) / self.cell)))
        x1 = min(self.ncols - 1, int(math.floor((lon_max - self.lon0) / self.cell)))
        y0 = max(0, int(math.floor((lat_min - self.lat0) / self.cell)))
        y1 = min(self.nrows - 1, int(math.floor((lat_max - self.lat0) / self.cell)))
        if x1 < x0 or y1 < y0:
            return np.zeros(0, np.int64)
        rows = np.arange(y0, y1 + 1) * self.ncols
        a = self.start[rows + x0]
        b = self.start[rows + x1 + 1]
        found = self.order[_ranges(a, b)].astype(np.int64)
        return np.unique(found) if unique else found

    def arrays(self, name):
        meta = np.array([self.lon0, self.lat0, self.cell, self.ncols, self.nrows])
        return {f"{name}.meta": meta, f"{name}.order": self.order,
                f"{name}.start": self.start}

    @classmethod
    def load(cls, arrays, name):
        lon0, lat0, cell, ncols, nrows = arrays[f"{name}.meta"]
        return cls(lon0, lat0, cell, ncols, nrows, arrays[f"{name}.order"],
                   arrays[f"{name}.start"])


def _ranges(a, b):
    """The concatenation of arange(a[i], b[i]) for every i, without a loop."""
    a = np.asarray(a, np.int64)
    n = np.maximum(np.asarray(b, np.int64) - a, 0)
    total = int(n.sum())
    if not total:
        return np.zeros(0, np.int64)
    keep = n > 0
    a, n = a[keep], n[keep]
    return np.repeat(a - np.cumsum(n) + n, n) + np.arange(total)
