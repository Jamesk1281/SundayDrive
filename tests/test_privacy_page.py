"""The public privacy page: present, self-contained, and not published unfinished.

`site/privacy/index.html` is what App Store Connect's privacy-policy URL points
at (`.github/workflows/pages.yml` deploys `site/`). A privacy page that pulls a
script or a web font from someone else's server contradicts itself, and one
that still says CONTACT_ADDRESS_TBD is not a policy anyone can act on.
See `docs/privacy-policy-page-brief.md`.
"""

from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parent.parent / "site" / "privacy" / "index.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_privacy_page_exists():
    assert PAGE.is_file()


@pytest.mark.parametrize("external", ["<script src", "fonts.googleapis"])
def test_privacy_page_loads_nothing_external(external):
    assert external not in _page().lower()


def test_privacy_page_has_a_contact_address():
    page = _page()
    assert "CONTACT_ADDRESS_TBD" not in page
    assert "privacy@jameskouvlis.com" in page
