# SPDX-License-Identifier: Apache-2.0
"""Memory backend abstraction (REC-018).

Public surface::

    from eidolon.memory import MemoryAdapter, InMemAdapter, HindsightAdapter, load_adapter

Operators who write custom adapters subclass :class:`MemoryAdapter` and
register the class via ``memory.backend`` in their Hermes config.
"""

from eidolon.memory.adapter import MemoryAdapter
from eidolon.memory.inmem import InMemAdapter
from eidolon.memory.hindsight import HindsightAdapter
from eidolon.memory.loader import load_adapter

__all__ = [
    "MemoryAdapter",
    "InMemAdapter",
    "HindsightAdapter",
    "load_adapter",
]
