import pytest
from app.api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()

def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hello from img-service" in response.data
