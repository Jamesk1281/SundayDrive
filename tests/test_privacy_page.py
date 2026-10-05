"""The public privacy page: present, self-contained, and not published unfinished.

`site/privacy/index.html` is what App Store Connect's privacy-policy URL points
at (`.github/workflows/pages.yml` deploys `site/`). A privacy page that pulls a
script or a web font from someone else's server contradicts itself, and one
that still says CONTACT_ADDRESS_TBD is not a policy anyone can act on.
See `docs/privacy-policy.md`.

The page also quotes the app's location prompt word for word, so it has to
change whenever `ios/project.yml` does. It once went on quoting a prompt that
described one use of location while the app had more, and nothing noticed. See
`docs/location-text-and-contact.md`.
"""

import html
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "privacy" / "index.html"
PROJECT = ROOT / "ios" / "project.yml"
POLICY_SOURCE = ROOT / "docs" / "privacy-policy.md"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _location_prompt() -> str:
    """`NSLocationWhenInUseUsageDescription`, as `ios/project.yml` sets it.

    Read with a pattern rather than a YAML parser, which the venv does not
    have. That holds the key to one line and double quotes, as it is written
    today, and fails loudly rather than guessing at any other form. A YAML
    double-quoted string with no escapes in it reads the same as JSON.
    """
    values = re.findall(r"^\s*NSLocationWhenInUseUsageDescription:\s*(.*?)\s*$",
                        PROJECT.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(values) == 1, f"expected the key once in {PROJECT.name}, found {len(values)}"
    value = values[0]
    assert value.startswith('"') and value.endswith('"'), (
        f"expected a one-line double-quoted string, got {value!r}")
    return json.loads(value)


def _quoted_prompt() -> str:
    """The text of the page's `<blockquote id="location-purpose">`, as rendered."""
    found = re.search(r'<blockquote id="location-purpose">(.*?)</blockquote>', _page(), re.DOTALL)
    assert found, 'the page has no <blockquote id="location-purpose">'
    return " ".join(html.unescape(found.group(1)).split())


def test_privacy_page_exists():
    assert PAGE.is_file()


@pytest.mark.parametrize("external", ["<script src", "fonts.googleapis"])
def test_privacy_page_loads_nothing_external(external):
    assert external not in _page().lower()


def test_privacy_page_has_a_contact_address():
    page = _page()
    assert "CONTACT_ADDRESS_TBD" not in page
    assert "privacy@jameskouvlis.com" in page


def test_privacy_page_quotes_the_location_prompt_exactly():
    assert _quoted_prompt() == _location_prompt()


def test_policy_source_quotes_the_location_prompt():
    # The source copy wraps its lines, so compare with whitespace collapsed.
    source = " ".join(POLICY_SOURCE.read_text(encoding="utf-8").split())
    assert _location_prompt() in source
