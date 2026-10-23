"""The public support page: present, self-contained, and linked so Pages serves it.

`site/index.html` is what App Store Connect's Support URL points at,
https://jamesk1281.github.io/SundayDrive/ (`.github/workflows/pages.yml`
deploys `site/`). App Review guideline 1.5 wants a way to contact the developer
from it, which a redirect to the privacy policy is not. Pages serves this repo
as a project site under /SundayDrive/, so `href="/privacy/"` would resolve to
jamesk1281.github.io/privacy/ and 404: links have to be relative.
The brief it was built from: `git show a2ddddc:docs/support-page-brief.md`.
"""

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parent.parent / "site" / "index.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_support_page_exists():
    assert PAGE.is_file()


@pytest.mark.parametrize("external", ["<script src", "fonts.googleapis", 'src="http'])
def test_support_page_loads_nothing_external(external):
    assert external not in _page().lower()


def test_support_page_loads_no_stylesheet_from_elsewhere():
    assert re.search(r'href="http[^"]*\.css', _page().lower()) is None


def test_support_page_is_not_a_redirect():
    assert 'http-equiv="refresh"' not in _page().lower()


def test_support_page_has_the_contact_address():
    assert "mailto:support@jameskouvlis.com" in _page()


def test_support_page_links_are_relative():
    page = _page()
    assert 'href="privacy/"' in page
    assert 'href="/' not in page


# The support page's credits are the Sources screen's, word for word
# (docs/national-copy.md, "The support page's credits"). Read from the Swift
# source, so a source added to the app and not to the page fails here.
ABOUT = PAGE.parent.parent / "ios" / "Sources" / "AboutView.swift"


def _swift_strings(block: str) -> list[str]:
    """The string values in a Swift array or argument list: literals joined by
    `+` are one value, a comma starts the next."""
    values, current = [], None
    for token in re.findall(r'"((?:[^"\\]|\\.)*)"|(\+)|(,)', block):
        literal, plus, comma = token
        if comma:
            if current is not None:
                values.append(current)
            current = None
        elif not plus:
            current = (current or "") + literal
    if current is not None:
        values.append(current)
    return values


def _sources() -> list[dict]:
    swift = ABOUT.read_text(encoding="utf-8")
    sources = []
    for body in re.findall(r"= DataSource\((.*?)\n    \)", swift, re.S):
        name = _swift_strings(re.search(r'name: (".*?"),\n', body).group(1))[0]
        credit = _swift_strings(re.search(r"credit: \[(.*?)\]", body, re.S).group(1))
        licence = re.search(r'licence: ("[^"]*"|nil)', body).group(1)
        sources.append({"name": name, "credit": credit,
                        "licence": None if licence == "nil" else licence.strip('"')})
    return sources


def _odbl_method() -> str:
    swift = ABOUT.read_text(encoding="utf-8")
    return _swift_strings(re.search(r"static let odblMethod = (.*?)\n\n", swift, re.S).group(1))[0]


def _page_text() -> str:
    import html
    text = re.sub(r"<!--.*?-->", " ", _page(), flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text)


def test_the_sources_screen_parses():
    names = [s["name"] for s in _sources()]
    assert len(names) == 7, names
    assert "OpenStreetMap" in names and "Apple Maps" in names


@pytest.mark.parametrize("source", _sources(), ids=lambda s: s["name"])
def test_every_source_on_the_screen_is_credited_on_the_page(source):
    text = _page_text()
    assert source["name"] in text
    for line in source["credit"]:
        assert line in text, line
    if source["licence"]:
        assert source["licence"] in text


def test_the_page_carries_the_odbl_method_line():
    assert _odbl_method() in _page_text()
    assert 'href="https://github.com/Jamesk1281/SundayDrive"' in _page()
