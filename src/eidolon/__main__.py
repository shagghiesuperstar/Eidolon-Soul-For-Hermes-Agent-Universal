# SPDX-License-Identifier: Apache-2.0
"""Allow `python -m eidolon ...` to invoke the CLI."""

from eidolon.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
