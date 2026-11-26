# SPDX-License-Identifier: GPL-3.0-or-later
"""Load the external SFTP sources for unit tests without changing sys.path."""
import importlib
import importlib.util
import sys
from pathlib import Path

PACKAGE = "_termia_sftp_unit_tests"
SOURCE = (Path(__file__).resolve().parents[1]
          / "sftp/src/termia_sftp")


def plugin_module(name):
    if PACKAGE not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            PACKAGE, SOURCE / "__init__.py", submodule_search_locations=[str(SOURCE)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[PACKAGE] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            del sys.modules[PACKAGE]
            raise
    return importlib.import_module(f"{PACKAGE}.{name}")
