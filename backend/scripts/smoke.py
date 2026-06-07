from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        print(client.get("/healthz").json())


if __name__ == "__main__":
    main()

