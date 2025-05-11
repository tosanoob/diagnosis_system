import uuid
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.sqlite_service import Base
from app.core.datetime_helper import now_utc

def generate_uuid():
    """Generate unique ID"""
    return str(uuid.uuid4())

class Disease(Base):
    __tablename__ = "diseases"

    id = Column(String, primary_key=True, default=generate_uuid)
    label = Column(String, nullable=False)
    domain_id = Column(String, ForeignKey("domains.id"))
    description = Column(Text)
    included_in_diagnosis = Column(Boolean, default=True)
    article_id = Column(String, ForeignKey("articles.id"))
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(String)
    updated_by = Column(String)
    deleted_by = Column(String)
    
    # Relationships
    domain = relationship("Domain", back_populates="diseases")
    article = relationship("Article", back_populates="diseases")
    diagnosis_logs = relationship("DiagnosisLogDisease", back_populates="disease")

class Domain(Base):
    __tablename__ = "domains"

    id = Column(String, primary_key=True, default=generate_uuid)
    domain = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(String)
    updated_by = Column(String)
    deleted_by = Column(String)
    
    # Relationships
    diseases = relationship("Disease", back_populates="domain")
    disease_crossmaps_1 = relationship("DiseaseDomainCrossmap", foreign_keys="DiseaseDomainCrossmap.domain_id_1", back_populates="domain_1")
    disease_crossmaps_2 = relationship("DiseaseDomainCrossmap", foreign_keys="DiseaseDomainCrossmap.domain_id_2", back_populates="domain_2")

class DiseaseDomainCrossmap(Base):
    __tablename__ = "disease_domain_crossmap"

    id = Column(String, primary_key=True, default=generate_uuid)
    disease_id_1 = Column(String, ForeignKey("diseases.id"))
    domain_id_1 = Column(String, ForeignKey("domains.id"))
    disease_id_2 = Column(String, ForeignKey("diseases.id"))
    domain_id_2 = Column(String, ForeignKey("domains.id"))
    
    # Relationships
    disease_1 = relationship("Disease", foreign_keys=[disease_id_1])
    domain_1 = relationship("Domain", foreign_keys=[domain_id_1], back_populates="disease_crossmaps_1")
    disease_2 = relationship("Disease", foreign_keys=[disease_id_2])
    domain_2 = relationship("Domain", foreign_keys=[domain_id_2], back_populates="disease_crossmaps_2")

class DiagnosisLog(Base):
    __tablename__ = "diagnosis_log"

    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=now_utc)
    image_content = Column(Text)
    text_content = Column(Text)
    result_text = Column(Text)
    result_reasoning = Column(Text)
    
    # Relationships
    diseases = relationship("DiagnosisLogDisease", back_populates="diagnosis_log")

class DiagnosisLogDisease(Base):
    __tablename__ = "diagnosis_log_disease"

    id = Column(String, primary_key=True, default=generate_uuid)
    diagnosis_log_id = Column(String, ForeignKey("diagnosis_log.id"))
    disease_id = Column(String, ForeignKey("diseases.id"))
    
    # Relationships
    diagnosis_log = relationship("DiagnosisLog", back_populates="diseases")
    disease = relationship("Disease", back_populates="diagnosis_logs")

class Role(Base):
    __tablename__ = "role"

    role_id = Column(String, primary_key=True, default=generate_uuid)
    role = Column(String, nullable=False)
    
    # Relationships
    users = relationship("UserInfo", back_populates="role")

class UserToken(Base):
    __tablename__ = "user_token"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("user_info.user_id"))
    token_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=now_utc)
    expired_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    
    # Relationships
    user = relationship("UserInfo", back_populates="tokens")

class UserInfo(Base):
    __tablename__ = "user_info"

    user_id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, nullable=False, unique=True)
    hashpass = Column(String, nullable=False)
    role_id = Column(String, ForeignKey("role.role_id"))
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    deleted_at = Column(DateTime)
    
    # Relationships
    role = relationship("Role", back_populates="users")
    tokens = relationship("UserToken", back_populates="user")
    created_articles = relationship("Article", foreign_keys="Article.created_by", primaryjoin="UserInfo.user_id==Article.created_by")
    updated_articles = relationship("Article", foreign_keys="Article.updated_by", primaryjoin="UserInfo.user_id==Article.updated_by")
    deleted_articles = relationship("Article", foreign_keys="Article.deleted_by", primaryjoin="UserInfo.user_id==Article.deleted_by")

class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    summary = Column(Text)
    content = Column(Text)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    deleted_at = Column(DateTime)
    created_by = Column(String, ForeignKey("user_info.user_id"))
    updated_by = Column(String, ForeignKey("user_info.user_id"))
    deleted_by = Column(String, ForeignKey("user_info.user_id"))
    
    # Relationships
    diseases = relationship("Disease", back_populates="article")

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text)
    location = Column(Text)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
    deleted_at = Column(DateTime)
    created_by = Column(String, ForeignKey("user_info.user_id"))
    updated_by = Column(String, ForeignKey("user_info.user_id"))
    deleted_by = Column(String, ForeignKey("user_info.user_id"))
    phone_number = Column(String)
    website = Column(String)

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=now_utc)
    deleted_at = Column(DateTime)
    title = Column(String, nullable=False)
    description = Column(Text)

# Image management models
class Image(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True, default=generate_uuid)
    base_url = Column(String, nullable=False)
    rel_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=now_utc)
    uploaded_by = Column(String, ForeignKey("user_info.user_id"))
    
    # Relationships
    uploader = relationship("UserInfo", foreign_keys=[uploaded_by])
    image_maps = relationship("ImageMap", back_populates="image")

class ImageUsage(Base):
    __tablename__ = "image_usage"

    usage = Column(String, primary_key=True)
    description = Column(Text)
    
    # Relationships
    image_maps = relationship("ImageMap", back_populates="usage_type")

class ImageMap(Base):
    __tablename__ = "image_map"

    id = Column(String, primary_key=True, default=generate_uuid)
    image_id = Column(String, ForeignKey("images.id"))
    object_type = Column(String, nullable=False)  # 'disease', 'clinic', 'article'
    object_id = Column(String, nullable=False)
    usage = Column(String, ForeignKey("image_usage.usage"))  # 'thumbnail', 'cover'
    
    # Relationships
    image = relationship("Image", back_populates="image_maps")
    usage_type = relationship("ImageUsage", back_populates="image_maps") 