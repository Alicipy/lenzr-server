"""Export the OpenAPI schema from the FastAPI app to stdout."""

import json

from lenzr_server.main import app

print(json.dumps(app.openapi(), indent=2))
