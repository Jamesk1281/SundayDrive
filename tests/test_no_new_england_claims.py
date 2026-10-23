"""No customer-facing text says the app covers New England.

The binary covers the 48 contiguous states and DC, and the 2026-10-23 outside
review found every text a customer or App Review reads still describing a
six-state app. This fails if a New England coverage claim, or one of New
England's network figures, comes back into any of them
(docs/national-copy.md §7).

Not every "New England" is wrong. A claim *scoped* to where it was measured,
such as the rating figures from the developer's own New England drives, is
true and deliberate (docs/marketing-plan.md §3.4). Those are allowed one by
one in `ALLOWED`, each with its reason, and an entry that no longer matches
anything fails too, so the list cannot outlive the text it excuses.

What is read is what reaches a reader, not the maintainers' notes around it:
the fenced `text` blocks that get pasted into App Store Connect, the visible
text of the two web pages, §§0-6 of the privacy policy's source, the README's
opening paragraph, the screenshot captions, and every string literal in the
app's Swift sources.
"""

import ast
import html
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# New England as coverage, and New England's own network figures
# (docs/marketing-plan.md §0, item 4).
CLAIM = re.compile(
    r"new england|six (?:new england )?states|six-state|"
    r"146,811|146,000|236,000|942,448|998k",
    re.IGNORECASE,
)

# (where, the exact text that may say it, why it is true and stays).
ALLOWED = [
    ("docs/app-store-listing.md",
     "Over 79 ratings the developer made on test drives in New England",
     "The featuring nomination's private notes, read by Apple's editors only. "
     "marketing-plan.md §3.4 allows the 79-rating separation there and only "
     "there, scoped to New England and one rater, which the sentence does."),
    ("docs/privacy-policy.md",
     "incomplete before the New England check existed",
     "History: says what the policy used to say before 2026-10-04, when the "
     "check was New England's. It describes the past, not the coverage."),
    ("README.md",
     "The test drives that checked the score were all in New England",
     "A scoped truth: every recorded drive and mark is from New England, and "
     "the README's measured claims (ETA, scenery) rest on them."),
]


def _fenced_text(rel):
    return "\n".join(re.findall(r"```text\n(.*?)\n```", (REPO / rel).read_text(), re.S))


def _visible(rel):
    page = re.sub(r"<!--.*?-->|<style.*?</style>", " ", (REPO / rel).read_text(), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def _policy_body(rel):
    text = (REPO / rel).read_text()
    return text[text.index("## 0. "):text.index("## 7. ")]


def _readme_opening(rel):
    text = (REPO / rel).read_text()
    return text.split("\n\n")[1]


def _python_strings(rel):
    """Every string constant in the module that is not a docstring."""
    tree = ast.parse((REPO / rel).read_text())
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
                  and node.body and isinstance(node.body[0], ast.Expr)
                  and isinstance(node.body[0].value, ast.Constant)}
    return "\n".join(node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Constant) and isinstance(node.value, str)
                     and id(node) not in docstrings)


def _swift_literals(path):
    """Every string literal in a Swift file, comments dropped."""
    found = []
    for line in path.read_text().splitlines():
        i, n = 0, len(line)
        while i < n:
            if line.startswith("//", i):
                break
            if line[i] == '"':
                j, buf = i + 1, []
                while j < n and line[j] != '"':
                    if line[j] == "\\" and j + 1 < n:
                        buf.append(line[j:j + 2])
                        j += 2
                        continue
                    buf.append(line[j])
                    j += 1
                found.append("".join(buf))
                i = j + 1
                continue
            i += 1
    return "\n".join(found)


def _texts():
    texts = {
        "docs/app-store-listing.md": _fenced_text("docs/app-store-listing.md"),
        "docs/app-store-submission.md": _fenced_text("docs/app-store-submission.md"),
        "site/index.html": _visible("site/index.html"),
        "site/privacy/index.html": _visible("site/privacy/index.html"),
        "docs/privacy-policy.md": _policy_body("docs/privacy-policy.md"),
        "README.md": _readme_opening("README.md"),
        "app-store-screenshots/build.py": _python_strings("app-store-screenshots/build.py"),
    }
    for path in sorted((REPO / "ios" / "Sources").glob("*.swift")):
        texts[str(path.relative_to(REPO))] = _swift_literals(path)
    # One space between words, so a phrase wrapped across lines still matches.
    return {where: re.sub(r"\s+", " ", text) for where, text in texts.items()}


TEXTS = _texts()


def _claims(where, text):
    """Each claim in `text` that no allowed phrase contains, with context."""
    spans = [(m.start(), m.end())
             for w, phrase, _ in ALLOWED if w == where
             for m in re.finditer(re.escape(phrase), text)]
    return [text[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")
            for m in CLAIM.finditer(text)
            if not any(lo <= m.start() and m.end() <= hi for lo, hi in spans)]


def test_every_text_was_read():
    # A renamed heading or file would otherwise turn a check into a pass.
    for where, text in TEXTS.items():
        if where.startswith("ios/"):
            continue
        assert len(text) > 500, where
    assert sum(where.startswith("ios/") for where in TEXTS) > 20


@pytest.mark.parametrize("where", sorted(TEXTS))
def test_no_new_england_coverage_claim(where):
    assert _claims(where, TEXTS[where]) == []


@pytest.mark.parametrize("where, phrase, reason", ALLOWED, ids=[a[0] for a in ALLOWED])
def test_every_allowed_phrase_is_still_there(where, phrase, reason):
    assert reason
    assert phrase in TEXTS[where], f"{phrase!r} is gone from {where}: drop its entry"


@pytest.mark.parametrize("sentence", [
    "Every road in New England, scored for scenery.",
    "Coverage is the six New England states.",
    "about 146,000 miles of road",
])
def test_the_pattern_catches_the_old_copy(sentence):
    assert _claims("site/index.html", sentence)
