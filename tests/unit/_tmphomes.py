"""Helper: create isolated HERMES_HOME + EIDOLON_HOME per test."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class IsolatedHome(unittest.TestCase):
    """Base class that gives each test its own HERMES_HOME + EIDOLON_HOME."""

    def setUp(self) -> None:  # noqa: D401 - unittest hook
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.hermes_home = self.tmp / "hermes"
        self.eidolon_home = self.tmp / "eidolon"
        self.hermes_home.mkdir(parents=True)
        self.eidolon_home.mkdir(parents=True)

        self._saved = {
            "HERMES_HOME": os.environ.get("HERMES_HOME"),
            "EIDOLON_HOME": os.environ.get("EIDOLON_HOME"),
        }
        os.environ["HERMES_HOME"] = str(self.hermes_home)
        os.environ["EIDOLON_HOME"] = str(self.eidolon_home)

    def tearDown(self) -> None:  # noqa: D401 - unittest hook
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def write_hermes_cache(self, providers: dict) -> Path:
        import json

        p = self.hermes_home / "provider_models_cache.json"
        p.write_text(json.dumps(providers), encoding="utf-8")
        return p

    def write_hermes_config(self, text: str) -> Path:
        p = self.hermes_home / "config.yaml"
        p.write_text(text, encoding="utf-8")
        return p
