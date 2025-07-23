import io
import pytest
from app.api.app import app, db, Image
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def client():
    app.config.from_object('app.config.TestingConfig')
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def test_upload_image_success(client, monkeypatch):
    # Mock verify_token pour simuler un utilisateur connecté
    def fake_verify_token(auth_header):
        return {'id': 'user123', 'email': 'test@example.com'}

    monkeypatch.setattr('app.api.app.verify_token', fake_verify_token)

    data = {
        'file': (io.BytesIO(b'mock image data'), 'test.jpg')
    }

    response = client.post('/upload', content_type='multipart/form-data', data=data)

    assert response.status_code == 201
    json_data = response.get_json()
    assert 'id' in json_data
    assert json_data['original_filename'] == 'test.jpg'

def test_upload_no_file(client, monkeypatch):
    def fake_verify_token(auth_header):
        return {'id': 'user123'}

    monkeypatch.setattr('app.api.app.verify_token', fake_verify_token)

    response = client.post('/upload')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'No file part'

def test_upload_unauthorized(client):
    response = client.post('/upload')
    assert response.status_code == 401
    assert response.get_json()['error'] == 'Unauthorized'
