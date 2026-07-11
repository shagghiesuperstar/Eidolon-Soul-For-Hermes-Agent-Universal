# SPDX-License-Identifier: Apache-2.0
"""Judgment Brain — classify Eidolon lessons into concrete Hermes actions.

This package is the missing arrow between Eidolon's dream cycle and Hermes
Agent actually getting smarter. A lesson that sits in MEMORY.md forever is
an intention, not a change. The Judgment Brain turns intentions into actions:

    lesson text
        → classify()     → ActionKind
        → execute()      → file written / line retired
        → metrics()      → integers you can plot

Exit-code contract (anti-fragile, never silent):
    All public functions return a result dict with 'status': 'ok' | 'skip' | 'fail'.
    Callers must check status; failures are never swallowed.
"""
from .classifier import ActionKind, classify_lesson
from .executor import execute_judgment
from .metrics import increment, load_metrics, record_judgment

__all__ = [
    "ActionKind",
    "classify_lesson",
    "execute_judgment",
    "increment",
    "load_metrics",
    "record_judgment",
]
