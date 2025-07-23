import uuid
from flask import Flask, request, jsonify
from app.models.db import db
from app.config import get_config
from dotenv import load_dotenv
import os
import boto3
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

import requests
from app.models.image import Image

load_dotenv()

app = Flask(__name__)
app.config.from_object(get_config())

# Initialisation de la base de données (SQLAlchemy)
db.init_app(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 Mo
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def verify_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]

    try:
        user_service_url = os.getenv("USER_SERVICE_URL", "http://user-service:5000/api/me")
        response = requests.get(user_service_url, headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return response.json()  # dict avec infos utilisateur
        else:
            return None
    except Exception:
        return None


@app.route('/upload', methods=['POST'])
def upload_image():
    auth = request.headers.get('Authorization')
    user_info = verify_token(auth)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        ext = original_filename.rsplit('.', 1)[1].lower()

        # Utiliser datetime avec timezone aware (UTC)
        filename = f"{user_info['id']}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
        content_type = file.content_type

        # Lit la taille sans vider le stream
        file_stream = file.stream
        file_stream.seek(0, os.SEEK_END)
        size = file_stream.tell()
        file_stream.seek(0)

        # Connexion boto3 vers MinIO
        s3 = boto3.client(
            's3',
            endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}",
            aws_access_key_id=os.getenv('MINIO_ROOT_USER'),
            aws_secret_access_key=os.getenv('MINIO_ROOT_PASSWORD'),
        )

        try:
            s3.upload_fileobj(
                file,
                os.getenv('MINIO_BUCKET'),
                filename,
                ExtraArgs={"ContentType": content_type}
            )
        except Exception as e:
            return jsonify({"error": "Failed to upload to storage", "details": str(e)}), 500

        try:
            # Convertir user_id en UUID (string UUID valide obligatoire)
            user_uuid = uuid.UUID(user_info['id'])

            # Création instance Image
            image = Image(
                user_id=user_uuid,
                filename_original=original_filename,
                filename_stored=filename,
                content_type=content_type,
                size=size
            )
            db.session.add(image)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Database error", "details": str(e)}), 500

        return jsonify({
            "id": str(image.id),
            "filename_original": image.filename_original,
            "filename_stored": image.filename_stored,
            "content_type": image.content_type,
            "size": image.size,
            "upload_date": image.upload_date.isoformat(),
            "user_id": str(image.user_id),
            "status": image.status.value
        }), 201

    return jsonify({"error": "Invalid file type"}), 400


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.logger.setLevel('DEBUG')  # active les logs DEBUG
    app.run(host="0.0.0.0", port=5002, debug=True)
