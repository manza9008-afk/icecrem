import os
import sys
from pathlib import Path

import uvicorn


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
LOG_FILE = BACKEND_DIR / "backend.runtime.log"

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "test_database")
os.environ.setdefault(
    "CORS_ORIGINS",
    ",".join(
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
    ),
)

os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

log_handle = LOG_FILE.open("a", encoding="utf-8", buffering=1)
sys.stdout = log_handle
sys.stderr = log_handle

print("Starting backend runtime...", flush=True)

uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")
