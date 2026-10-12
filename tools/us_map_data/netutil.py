"""Small HTTP helpers shared by the US map data survey scripts.

One request at a time, a fixed User-Agent and a pause between calls: several
of the hosts surveyed are government servers that block bursts, and a block is
recorded as an access finding rather than worked around
(docs/us-map-data-findings.md, "Access").

Named netutil, not http, because a file called http.py beside these scripts
would shadow the standard library's http package that urllib imports.
"""

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "SundayDrive-us-map-data-survey/1.0"
PAUSE_S = 0.25
_last = [0.0]


def _wait():
    gap = time.monotonic() - _last[0]
    if gap < PAUSE_S:
        time.sleep(PAUSE_S - gap)
    _last[0] = time.monotonic()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib turns a redirected HEAD into a GET, which starts streaming the
    whole file (a 1.2 GB extract, for California). Redirects are followed by
    hand instead, keeping the method."""

    def redirect_request(self, *args, **kwargs):
        return None


def _tls():
    # The python.org interpreter this venv is built on ships no CA store of its
    # own; certifi's is the one requests already uses here.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_opener = urllib.request.build_opener(_NoRedirect,
                                      urllib.request.HTTPSHandler(context=_tls()))


def request(url, method="GET", data=None, timeout=60, tries=3, headers=None, hops=5):
    """(status, headers, body bytes) for one request. Status 0 means the
    request never got an HTTP answer; `body` then holds the error text."""
    err = b""
    for attempt in range(tries):
        _wait()
        req = urllib.request.Request(url, method=method, data=data,
                                     headers={"User-Agent": UA, **(headers or {})})
        try:
            with _opener.open(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read() if method != "HEAD" else b""
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location") and hops:
                nxt = urllib.parse.urljoin(url, e.headers["Location"])
                return request(nxt, method=method, data=data, timeout=timeout,
                               tries=tries, headers=headers, hops=hops - 1)
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(2 * 2 ** attempt)
                continue
            return e.code, dict(e.headers or {}), e.read() if method != "HEAD" else b""
        except Exception as e:  # timeouts, resets, DNS
            err = f"{type(e).__name__}: {e}".encode()
            if attempt < tries - 1:
                time.sleep(2 * 2 ** attempt)
    return 0, {}, err


def head(url, **kw):
    """(status, Content-Length or None, headers)."""
    status, hdrs, _ = request(url, method="HEAD", **kw)
    size = hdrs.get("Content-Length")
    return status, (int(size) if size is not None else None), hdrs


def get_json(url, params=None, **kw):
    """(status, parsed JSON or None, raw body)."""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    status, _, body = request(url, **kw)
    try:
        return status, json.loads(body), body
    except (ValueError, UnicodeDecodeError):
        return status, None, body
