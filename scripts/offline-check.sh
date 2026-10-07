#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
for script in scripts/*.sh; do bash -n "$script"; done
python3 - <<'PYCODE'
import ast,json
from pathlib import Path
for directory in ['instrumented-api','notification-sink','scripts','tests']:
    for path in Path(directory).rglob('*.py'):ast.parse(path.read_text(),filename=str(path))
json.loads(Path('grafana/dashboards/netops.json').read_text())
print('Python/Bash syntax and dashboard JSON parsing: PASS')
PYCODE
