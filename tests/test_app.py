from fastapi.testclient import TestClient

from catchall.app import app

client = TestClient(app)

def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_homepage() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<html lang="en">' in response.text
    assert "<h1>CatchAll</h1>" in response.text
    assert 'role="status"' in response.text
    assert 'aria-live="polite"' in response.text
    assert "verbatim captions" in response.text.lower()
    assert "plain-language captions" in response.text.lower()

def test_stylesheet() -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]