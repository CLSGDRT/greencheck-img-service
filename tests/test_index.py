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
    return {'sub': str(uuid.uuid4()), 'email': 'test@example.com'}

@patch('app.api.app.boto3.client')
def test_upload_image_success(mock_boto_client, client, monkeypatch):
    mock_s3 = MagicMock()
    mock_s3.upload_fileobj.return_value = None
    mock_boto_client.return_value = mock_s3

    monkeypatch.setattr('app.api.app.jwt_verifier.verify_token', fake_verify_token)

    data = {
        'file': (io.BytesIO(b'mock image data'), 'test.jpg')
    }

    response = client.post('/upload', content_type='multipart/form-data', data=data)
    assert response.status_code == 201
    json_data = response.get_json()
    assert 'id' in json_data
    assert json_data['filename_original'] == 'test.jpg'

def test_upload_no_file(client, monkeypatch):
    monkeypatch.setattr('app.api.app.jwt_verifier.verify_token', fake_verify_token)
    response = client.post('/upload')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'No file part'

def test_upload_unauthorized(client):
    response = client.post('/upload')
    assert response.status_code == 401
    assert response.get_json()['error'] == 'Unauthorized'

@patch('app.api.app.boto3.client')
def test_get_images_success(mock_boto_client, client, monkeypatch):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    user_id = uuid.uuid4()

    with app.app_context():
        image = Image(
            id=uuid.uuid4(),
            user_id=user_id,
            filename_original='img.jpg',
            filename_stored='uuid.jpg',
            content_type='image/jpeg',
            size=1234
        )
        db.session.add(image)
        db.session.commit()

    monkeypatch.setattr('app.api.app.jwt_verifier.verify_token', lambda h: {'sub': str(user_id)})

    response = client.get('/images')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, list)
    assert json_data[0]['filename_original'] == 'img.jpg'

@patch('app.api.app.boto3.client')
def test_delete_image_success(mock_boto_client, client, monkeypatch):
    mock_s3 = MagicMock()
    mock_s3.delete_object.return_value = None
    mock_boto_client.return_value = mock_s3

    user_id = uuid.uuid4()
    image_id = uuid.uuid4()

    with app.app_context():
        image = Image(
            id=image_id,
            user_id=user_id,
            filename_original='img.jpg',
            filename_stored='uuid.jpg',
            content_type='image/jpeg',
            size=1234
        )
        db.session.add(image)
        db.session.commit()

    monkeypatch.setattr('app.api.app.jwt_verifier.verify_token', lambda h: {'sub': str(user_id)})

    response = client.delete(f'/images/{image_id}')
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Image deleted successfully'
