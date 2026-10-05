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
