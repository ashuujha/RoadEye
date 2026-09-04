import json
from pathlib import Path

from apps.api.main import app

Path("packages/roadeye/openapi.json").write_text(
    json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
)
