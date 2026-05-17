"""Pytest configuration for repository-local imports.

Pytest can start collection with either the repository root or the tests
directory at the front of ``sys.path`` depending on how it is invoked.  Keep
the root importable so tests can consistently import modules from ``scripts``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
