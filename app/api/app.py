import uuid
import os
import boto3
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

from app.models.db import db
from app.config import get_config
from app.models.image import Image
from app.utils.verify_jwt import JWTVerifier  # ✅ Classe propre

# Chargement des variables d’environnement
load_dotenv()

# Initialisation Flask
app = Flask(__name__)
app.config.from_object(get_config())
db.init_app(app)

# JWT verifier
jwt_verifier = JWTVerifier()

# Configuration des fichiers
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 Mo
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_image():
    auth = request.headers.get('Authorization')
    user_info = jwt_verifier.verify_token(auth)
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
        filename = f"{user_info['sub']}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
        content_type = file.content_type

        file_stream = file.stream
        file_stream.seek(0, os.SEEK_END)
        size = file_stream.tell()
        file_stream.seek(0)

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
            user_uuid = uuid.UUID(user_info['sub'])

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

        return jsonify(image.to_dict()), 201

    return jsonify({"error": "Invalid file type"}), 400


@app.route('/images/<image_id>', methods=['GET'])
def get_image_metadata(image_id):
    auth = request.headers.get('Authorization')
    user_info = jwt_verifier.verify_token(auth)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        image = db.session.get(Image, uuid.UUID(image_id))
        if not image:
            return jsonify({"error": "Image not found"}), 404

        if str(image.user_id) != user_info['sub']:
            return jsonify({"error": "Forbidden"}), 403

        return jsonify(image.to_dict()), 200

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


@app.route('/images/<image_id>/download', methods=['GET'])
def download_image(image_id):
    auth = request.headers.get('Authorization')
    user_info = jwt_verifier.verify_token(auth)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        image = db.session.get(Image, uuid.UUID(image_id))
        if not image:
            return jsonify({"error": "Image not found"}), 404

        if str(image.user_id) != user_info['sub']:
            return jsonify({"error": "Forbidden"}), 403

        s3 = boto3.client(
            's3',
            endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}",
            aws_access_key_id=os.getenv('MINIO_ROOT_USER'),
            aws_secret_access_key=os.getenv('MINIO_ROOT_PASSWORD'),
        )

        obj = s3.get_object(Bucket=os.getenv('MINIO_BUCKET'), Key=image.filename_stored)
        return Response(
            obj['Body'].read(),
            mimetype=image.content_type,
            headers={"Content-Disposition": f"inline; filename={image.filename_original}"}
        )

    except Exception as e:
        return jsonify({"error": "Failed to retrieve image", "details": str(e)}), 500


@app.route('/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    auth = request.headers.get('Authorization')
    user_info = jwt_verifier.verify_token(auth)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        image = db.session.get(Image, uuid.UUID(image_id))
        if not image:
            return jsonify({"error": "Image not found"}), 404

        if str(image.user_id) != user_info['sub']:
            return jsonify({"error": "Forbidden"}), 403

        s3 = boto3.client(
            's3',
            endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}",
            aws_access_key_id=os.getenv('MINIO_ROOT_USER'),
            aws_secret_access_key=os.getenv('MINIO_ROOT_PASSWORD'),
        )

        s3.delete_object(Bucket=os.getenv('MINIO_BUCKET'), Key=image.filename_stored)

        db.session.delete(image)
        db.session.commit()

        return jsonify({"message": "Image deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Deletion failed", "details": str(e)}), 500

@app.route('/images', methods=['GET'])
def get_images():
    auth = request.headers.get('Authorization')
    user_info = jwt_verifier.verify_token(auth)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        images = Image.query.filter_by(user_id=uuid.UUID(user_info['sub'])).all()
        return jsonify([img.to_dict() for img in images]), 200
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.logger.setLevel('DEBUG')
    app.run(host="0.0.0.0", port=5002, debug=True)
