# GWW Network Trace
![tests](https://github.com/timothy-holmes/gww-network-trace/workflows/Tests/badge.svg)
[![codecov.io](https://codecov.io/github/timothy-holmes/gww-network-trace/coverage.svg?branch=main)](https://codecov.io/github/timothy-holmes/gww-network-trace?branch=main)
![release](https://github.com/timothy-holmes/gww-network-trace/workflows/Release/badge.svg)

[![GPLv2 license](https://img.shields.io/badge/License-GPLv2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

## Development

Create a virtual environment with the following command:
```console
python create_qgis_venv.py
```

For more detailed development instructions see [development](docs/development.md).

### VsCode setup

On VS Code use the workspace [gww-network-trace.code-workspace](gww-network-trace.code-workspace).
The workspace contains all the settings and extensions needed for development.

Select the Python interpreter with Command Palette (Ctrl+Shift+P). Select `Python: Select Interpreter` and choose
the one with the path `.venv\Scripts\python.exe`.

## License
This plugin is distributed under the terms of the [GNU General Public License, version 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html) license.

See [LICENSE](LICENSE) for more information.
