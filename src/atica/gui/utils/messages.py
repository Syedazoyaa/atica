"""Wording of validation messages: the user reads the labels on the form, never internal names (Qt-free).

The calculation library names its arguments (``sent_to_rework``); these helpers translate such names
into what is written on the screen.  They change wording only, never what is accepted or rejected.
"""

from __future__ import annotations

import re
from typing import Mapping, Optional, Set, Tuple

#: the library's hint for a malformed number is meant for programmers
_DEVELOPER_HINT = "Pass an int, Decimal"
_PLAIN_NUMBER_HINT = "Use digits with a dot for decimals, for example 12.5."


def clean_label(text: str) -> str:
    """A field label as it reads inside a sentence: without ``(optional)`` and a leading ``...or``."""
    text = re.sub(r"\s*\(optional\)", "", text).strip()
    if text.startswith("...or "):
        text = text[len("...or ") :]
        text = text[:1].upper() + text[1:]
    return text


def plain_hint(hint: Optional[str]) -> Optional[str]:
    """Replace developer advice with advice for someone filling in a form."""
    return _PLAIN_NUMBER_HINT if hint and hint.startswith(_DEVELOPER_HINT) else hint


def enter_number(label: str, *, blank: bool) -> str:
    return "Enter %s number for %s." % ("a" if blank else "a valid", clean_label(label))


def translate(text: str, labels: Mapping[str, str]) -> Tuple[str, Set[str]]:
    """Replace the argument names in ``labels`` (name -> field label) found in ``text``.

    Returns the new text and the names that were found.  All names are replaced in one pass, so a name
    is never replaced again inside a label that was just inserted.
    """
    if not text or not labels:
        return text, set()
    pattern = re.compile(r"\b(%s)\b" % "|".join(sorted(map(re.escape, labels), key=len, reverse=True)))
    found: Set[str] = set()

    def swap(match: re.Match[str]) -> str:
        found.add(match.group(1))
        return "‘%s’" % clean_label(labels[match.group(1)])

    return pattern.sub(swap, text), found
