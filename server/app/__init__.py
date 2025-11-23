# Package marker for FastAPI application modules.
# Allows 'import app.main' in tests and runtime contexts.

import os

__version__ = os.getenv("APP_VERSION", "0.0.0")  