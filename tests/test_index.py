import uuid
import io
import pytest
from unittest.mock import patch, MagicMock
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

def fake_verify_token(auth_header):
    # UUID valide simulé
    return {'id': str(uuid.uuid4()), 'email': 'test@example.com'}

@patch('app.api.app.boto3.client')
def test_upload_image_success(mock_boto_client, client, monkeypatch):
    # Mock boto3 S3 client upload_fileobj method
    mock_s3 = MagicMock()
    mock_s3.upload_fileobj.return_value = None
    mock_boto_client.return_value = mock_s3

    # Mock verify_token to simulate authenticated user with UUID id
    monkeypatch.setattr('app.api.app.verify_token', fake_verify_token)

    data = {
        'file': (io.BytesIO(b'mock image data'), 'test.jpg')
    }

    response = client.post('/upload', content_type='multipart/form-data', data=data)

    assert response.status_code == 201
    json_data = response.get_json()
    assert 'id' in json_data
    assert json_data['filename_original'] == 'test.jpg'

def test_upload_no_file(client, monkeypatch):
    def fake_verify_token(auth_header):
        return {'id': str(uuid.uuid4())}

    monkeypatch.setattr('app.api.app.verify_token', fake_verify_token)

    response = client.post('/upload')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'No file part'

def test_upload_unauthorized(client):
    response = client.post('/upload')
    assert response.status_code == 401
    assert response.get_json()['error'] == 'Unauthorized'
