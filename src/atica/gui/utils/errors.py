"""User-facing error handling: friendly messages for the interface, diagnostics in a log file."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from atica.core import AticaError

from .messages import plain_hint

LOG = logging.getLogger("atica.gui")
T = TypeVar("T")


@dataclass
class FriendlyError:
    """What the user sees: never a traceback."""

    title: str
    message: str
    hint: Optional[str] = None
    parameter: Optional[str] = None  # form field to highlight
    unexpected: bool = False
    code: str = ""  # the library's stable error code


def describe(exc: BaseException) -> FriendlyError:
    """Translate any exception into something understandable (and log the unexpected ones)."""
    if isinstance(exc, AticaError):
        return FriendlyError(
            "Please check your input", exc.message, plain_hint(exc.hint), exc.parameter, code=exc.code
        )
    LOG.error("Unexpected error in the GUI", exc_info=exc)
    return FriendlyError(
        "Something went wrong",
        "ATICA could not complete this action. Your data was not changed.",
        "Details were written to the log file: %s" % (log_path() or "(logging unavailable)"),
        None,
        unexpected=True,
    )


def guard(action: Callable[[], T]) -> tuple[Optional[T], Optional[FriendlyError]]:
    """Run ``action``; return ``(value, None)`` or ``(None, FriendlyError)``. Nothing is swallowed silently."""
    try:
        return action(), None
    except Exception as exc:
        return None, describe(exc)


_log_file: Optional[str] = None


def log_path() -> Optional[str]:
    return _log_file


def setup_logging(directory: Optional[str]) -> Optional[str]:
    """Log warnings and errors to ``<directory>/atica-gui.log``; returns the path (or ``None``)."""
    global _log_file
    if not directory:
        return None
    try:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "atica-gui.log")
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        LOG.addHandler(handler)
        LOG.setLevel(logging.INFO)
        _log_file = path
        return path
    except OSError:
        return None
