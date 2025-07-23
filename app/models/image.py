import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.models.db import db


class ImageStatus(PyEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class Image(db.Model):
    __tablename__ = 'images'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename_original = Column(String(255), nullable=False)
    filename_stored = Column(String(255), nullable=False, unique=True)
    content_type = Column(String(50), nullable=False)
    size = Column(Integer, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user_id = Column(UUID(as_uuid=True), nullable=False)  # Référence vers le user-service
    diagnosis_id = Column(UUID(as_uuid=True), nullable=True)  # Référence future

    status = Column(Enum(ImageStatus), default=ImageStatus.PENDING, nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "filename_original": self.filename_original,
            "filename_stored": self.filename_stored,
            "content_type": self.content_type,
            "size": self.size,
            "upload_date": self.upload_date.isoformat(),
            "user_id": str(self.user_id),
            "diagnosis_id": str(self.diagnosis_id) if self.diagnosis_id else None,
            "status": self.status.value
        }
