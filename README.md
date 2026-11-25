# Termia plugins

Trusted external plugins for Termia experimental API 2. Diagnostics, Statistics and SCP
are distributed separately and currently declare version `0.1.0.dev0`. This local source tree is not a published
release. No packaged release assets have been published.

Plugins run in Termia's process with its permissions, without sandboxing. Install
only trusted code. Activation changes apply on Save; installing or updating code
requires restarting Termia. Existing Diagnostics users must install it manually.

## Layout

- `diagnostics/`: manifest, implementation and EN/ES/CA translations.
- `statistics/`: connection counts, session durations, dashboards and EN/ES/CA translations.
- `scp/`: contextual file selection, destination and progress UI for SCP uploads.
- `package_plugin.py`: reproducible per-plugin packaging from Git tar snapshots.
- `termia_plugins_tests/`: plugin unit, packaging and host integration tests.
- `LICENSE`: GPL-3.0-or-later; copied into each archive.

## Local validation

Keep this directory beside the compatible Termia checkout as `termia-plugins`.
From the Termia checkout, use its existing GTK test runner and dependencies:

```bash
python3 scripts/run_sandbox_tests.py
python3 scripts/run_sandbox_tests.py discover -s ../termia-plugins/termia_plugins_tests -t ../termia-plugins
python3 tools/addon-lab/run.py
```

The first command tests the host independently; the second tests the external
plugin and its integration. A missing external checkout is an error, not a skip.
The laboratory uses an isolated profile and honors `TERMIA_PLUGINS_DIR`; its
`--without-addon` mode runs without loading external plugins.

For a fresh combined line/branch measurement, run from the Termia checkout with
its existing Coverage installation and access to system GTK:

```bash
export TERMIA_SOURCE_DIR="$PWD"
export TERMIA_PLUGINS_SOURCE="$(realpath ../termia-plugins)"
export COVERAGE_RCFILE="$TERMIA_PLUGINS_SOURCE/.coveragerc"
test -f "$TERMIA_PLUGINS_SOURCE/diagnostics/plugin.json" &&
test -f "$TERMIA_PLUGINS_SOURCE/statistics/plugin.json" &&
test -f "$TERMIA_PLUGINS_SOURCE/scp/plugin.json" &&
coverage erase &&
coverage run scripts/run_sandbox_tests.py &&
coverage run scripts/run_sandbox_tests.py discover -s "$TERMIA_PLUGINS_SOURCE/termia_plugins_tests" -t "$TERMIA_PLUGINS_SOURCE" &&
coverage combine &&
coverage report &&
coverage html &&
coverage json -o htmlcov/coverage.json
unset COVERAGE_RCFILE TERMIA_SOURCE_DIR TERMIA_PLUGINS_SOURCE
```

Both runs produce subprocess data; combine only after both succeed. Verify every
application and plugin production module is present. Report separate Termia, Diagnostics, Statistics and SCP
line and branch totals as well as the combined result. No coverage exclusions or
minimum percentages apply. Reports remain ignored in Termia's `htmlcov/`.
Coverage maps the installed Statistics package exercised by the restart test back
to its source directory. Verify that Statistics has executed lines.
Coverage does not measure native GTK/VTE code or guarantee child data after an
abrupt process termination. Termia's combined CI configuration pins a compatible
plugin commit and requires both suites and complete production-module coverage
inventory. That repository and commit must be published before remote CI can run.
Local standalone Termia commands measure only the host.

## Packaging

The packager accepts a tar snapshot rooted at this directory, containing the
plugin and `LICENSE`. From this checkout, package the approved committed source:

```bash
mkdir -p dist
git archive --format=tar --output=dist/source.tar HEAD
python3 package_plugin.py diagnostics --snapshot dist/source.tar --output dist
python3 package_plugin.py scp --snapshot dist/source.tar --output dist
python3 package_plugin.py statistics --snapshot dist/source.tar --output dist
```

These commands produce `termia-plugin-diagnostics-0.1.0.dev0.tar.gz` and `termia-plugin-scp-0.1.0.dev0.tar.gz` as well as
`termia-plugin-statistics-0.1.0.dev0.tar.gz`, each with its own `.sha256` file. Existing outputs are not overwritten. Verify reproducibility and checksums
before distribution. Checksums detect corruption, not publisher authenticity.
Installation instructions are maintained in Termia's README in EN/ES/CA.
