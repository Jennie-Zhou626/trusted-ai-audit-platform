from __future__ import annotations

import json

import requests


API = "http://127.0.0.1:8000/api"


def main() -> None:
    requests.get(f"{API}/health", timeout=5).raise_for_status()
    response = requests.post(f"{API}/demo/seed-showcase", data={"reset": "true"}, timeout=30)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
