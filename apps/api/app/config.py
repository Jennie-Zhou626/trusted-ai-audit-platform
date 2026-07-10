from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "storage" / "runtime"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "platform.sqlite3"
DEPLOYMENT_PATH = ROOT_DIR / "contracts" / "deployment.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
