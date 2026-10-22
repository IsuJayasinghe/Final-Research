"""
Bridge to expose FastAPI application at the backend root directory.
"""
import sys
from pathlib import Path

# Add backend/berth to sys.path so app and models resolve properly
berth_dir = Path(__file__).resolve().parent / "berth"
if str(berth_dir) not in sys.path:
    sys.path.insert(0, str(berth_dir))

from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
