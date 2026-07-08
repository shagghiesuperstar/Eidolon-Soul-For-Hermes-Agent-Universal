# SPDX-License-Identifier: Apache-2.0
"""Eidolon — self-improvement layer for Hermes Agent.

Public surface:
- eidolon.cli.main        — CLI entry point (also exposed as `python -m eidolon`)
- eidolon.__version__     — Semantic version

Everything else is internal and may change between minor versions until 1.0.
"""

from ._version import __version__

__all__ = ["__version__"]
