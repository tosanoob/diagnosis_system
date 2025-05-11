import uuid
from typing import Optional, List, Dict, Any, Union, Type, TypeVar, Generic
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from pydantic import BaseModel

from app.core.datetime_helper import now_utc
from app.db.models import (
    Disease, Domain, DiseaseDomainCrossmap, DiagnosisLog, DiagnosisLogDisease,
    Role, UserToken, UserInfo, Article, Clinic, Report,
    Image, ImageUsage, ImageMap
)
from app.models.database import (
    DiseaseCreate, DiseaseUpdate, DomainCreate, DomainUpdate,
    DiseaseDomainCrossmapCreate, DiseaseDomainCrossmapUpdate,
    DiagnosisLogCreate, DiagnosisLogUpdate, DiagnosisLogDiseaseCreate, DiagnosisLogDiseaseUpdate,
    RoleCreate, RoleUpdate, UserTokenCreate, UserTokenUpdate,
    UserInfoCreate, UserInfoUpdate, ArticleCreate, ArticleUpdate,
    ClinicCreate, ClinicUpdate, ReportCreate, ReportUpdate,
    ImageCreate, ImageUpdate, ImageUsageCreate, ImageUsageUpdate,
    ImageMapCreate, ImageMapUpdate
)

# Generic type variables for the models
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

# Base CRUD class for common operations
class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: str) -> Optional[ModelType]:
        """Get a single item by ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple items with pagination"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new item"""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """Update an existing item"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        # Update only fields that are provided
        for field in update_data:
            if hasattr(db_obj, field) and update_data[field] is not None:
                setattr(db_obj, field, update_data[field])
        
        # Update updated_at if the field exists
        if hasattr(db_obj, "updated_at"):
            setattr(db_obj, "updated_at", now_utc())
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: str) -> Optional[ModelType]:
        """Hard delete an item by ID"""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def soft_delete(self, db: Session, *, id: str, deleted_by: Optional[str] = None) -> Optional[ModelType]:
        """Soft delete an item by setting deleted_at"""
        obj = db.query(self.model).get(id)
        if obj and hasattr(obj, "deleted_at"):
            setattr(obj, "deleted_at", now_utc())
            if hasattr(obj, "deleted_by") and deleted_by:
                setattr(obj, "deleted_by", deleted_by)
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def count(self, db: Session) -> int:
        """Count total number of items"""
        return db.query(func.count(self.model.id)).scalar()


# Specialized CRUD classes for different models

# Disease CRUD operations
class CRUDDisease(CRUDBase[Disease, DiseaseCreate, DiseaseUpdate]):
    def get_by_label(self, db: Session, label: str) -> Optional[Disease]:
        """Get a disease by its label"""
        return db.query(Disease).filter(Disease.label == label).first()
    
    def get_active_diseases(self, db: Session, skip: int = 0, limit: int = 100) -> List[Disease]:
        """Get active diseases (not deleted and included in diagnosis)"""
        return db.query(Disease).filter(
            Disease.deleted_at.is_(None), 
            Disease.included_in_diagnosis.is_(True)
        ).offset(skip).limit(limit).all()
    
    def get_by_domain_id(self, db: Session, domain_id: str, skip: int = 0, limit: int = 100) -> List[Disease]:
        """Get diseases by domain ID"""
        return db.query(Disease).filter(
            Disease.domain_id == domain_id,
            Disease.deleted_at.is_(None)
        ).offset(skip).limit(limit).all()
    
    def search_diseases(self, db: Session, search_term: str, skip: int = 0, limit: int = 100) -> List[Disease]:
        """Search diseases by label or description"""
        search_pattern = f"%{search_term}%"
        return db.query(Disease).filter(
            or_(
                Disease.label.ilike(search_pattern),
                Disease.description.ilike(search_pattern)
            ),
            Disease.deleted_at.is_(None)
        ).offset(skip).limit(limit).all()


# Domain CRUD operations
class CRUDDomain(CRUDBase[Domain, DomainCreate, DomainUpdate]):
    def get_by_name(self, db: Session, domain_name: str) -> Optional[Domain]:
        """Get a domain by its name"""
        return db.query(Domain).filter(Domain.domain == domain_name).first()

# DiseaseDomainCrossmap CRUD operations
class CRUDDiseaseDomainCrossmap(CRUDBase[DiseaseDomainCrossmap, DiseaseDomainCrossmapCreate, DiseaseDomainCrossmapUpdate]):
    def get_by_disease_and_domain(
        self, db: Session, disease_id_1: str, domain_id_1: str, disease_id_2: str, domain_id_2: str
    ) -> Optional[DiseaseDomainCrossmap]:
        """Get crossmap by disease and domain IDs"""
        return db.query(DiseaseDomainCrossmap).filter(
            DiseaseDomainCrossmap.disease_id_1 == disease_id_1,
            DiseaseDomainCrossmap.domain_id_1 == domain_id_1,
            DiseaseDomainCrossmap.disease_id_2 == disease_id_2,
            DiseaseDomainCrossmap.domain_id_2 == domain_id_2
        ).first()
    
    def get_mappings_for_disease(self, db: Session, disease_id: str, domain_id: str) -> List[DiseaseDomainCrossmap]:
        """Get all crossmaps for a specific disease and domain"""
        return db.query(DiseaseDomainCrossmap).filter(
            or_(
                and_(
                    DiseaseDomainCrossmap.disease_id_1 == disease_id,
                    DiseaseDomainCrossmap.domain_id_1 == domain_id
                ),
                and_(
                    DiseaseDomainCrossmap.disease_id_2 == disease_id,
                    DiseaseDomainCrossmap.domain_id_2 == domain_id
                )
            )
        ).all()


# DiagnosisLog CRUD operations
class CRUDDiagnosisLog(CRUDBase[DiagnosisLog, DiagnosisLogCreate, DiagnosisLogUpdate]):
    def create_with_diseases(
        self, db: Session, obj_in: DiagnosisLogCreate, disease_ids: List[str]
    ) -> DiagnosisLog:
        """Create a diagnosis log with associated diseases"""
        # Create the diagnosis log
        obj_data = obj_in.model_dump()
        db_obj = DiagnosisLog(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Add disease associations
        for disease_id in disease_ids:
            diagnosis_disease = DiagnosisLogDisease(
                diagnosis_log_id=db_obj.id,
                disease_id=disease_id
            )
            db.add(diagnosis_disease)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_with_diseases(self, db: Session, id: str) -> Optional[Dict[str, Any]]:
        """Get diagnosis log with its associated diseases"""
        diagnosis = db.query(DiagnosisLog).filter(DiagnosisLog.id == id).first()
        if not diagnosis:
            return None
        
        # Get associated diseases
        disease_relations = db.query(DiagnosisLogDisease).filter(
            DiagnosisLogDisease.diagnosis_log_id == id
        ).all()
        
        disease_ids = [relation.disease_id for relation in disease_relations]
        diseases = db.query(Disease).filter(Disease.id.in_(disease_ids)).all()
        
        # Convert to dictionary with diseases included
        result = {
            "id": diagnosis.id,
            "created_at": diagnosis.created_at,
            "image_content": diagnosis.image_content,
            "text_content": diagnosis.text_content,
            "result_text": diagnosis.result_text,
            "result_reasoning": diagnosis.result_reasoning,
            "diseases": diseases
        }
        
        return result
    
    def get_recent_diagnoses(self, db: Session, limit: int = 10) -> List[DiagnosisLog]:
        """Get most recent diagnoses"""
        return db.query(DiagnosisLog).order_by(DiagnosisLog.created_at.desc()).limit(limit).all()


# DiagnosisLogDisease CRUD operations
class CRUDDiagnosisLogDisease(CRUDBase[DiagnosisLogDisease, DiagnosisLogDiseaseCreate, DiagnosisLogDiseaseUpdate]):
    def get_by_diagnosis_and_disease(self, db: Session, diagnosis_log_id: str, disease_id: str) -> Optional[DiagnosisLogDisease]:
        """Get diagnosis-disease relation by both IDs"""
        return db.query(DiagnosisLogDisease).filter(
            DiagnosisLogDisease.diagnosis_log_id == diagnosis_log_id,
            DiagnosisLogDisease.disease_id == disease_id
        ).first()
    
    def get_by_diagnosis(self, db: Session, diagnosis_log_id: str) -> List[DiagnosisLogDisease]:
        """Get all disease relations for a diagnosis"""
        return db.query(DiagnosisLogDisease).filter(
            DiagnosisLogDisease.diagnosis_log_id == diagnosis_log_id
        ).all()
    
    def get_by_disease(self, db: Session, disease_id: str) -> List[DiagnosisLogDisease]:
        """Get all diagnosis relations for a disease"""
        return db.query(DiagnosisLogDisease).filter(
            DiagnosisLogDisease.disease_id == disease_id
        ).all()


# Role CRUD operations
class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def get_by_name(self, db: Session, role_name: str) -> Optional[Role]:
        """Get a role by its name"""
        return db.query(Role).filter(Role.role == role_name).first()
    
    def get(self, db: Session, id: str) -> Optional[Role]:
        """Override to use role_id instead of id"""
        return db.query(Role).filter(Role.role_id == id).first()
    
    def remove(self, db: Session, *, id: str) -> Optional[Role]:
        """Override to use role_id instead of id"""
        obj = db.query(Role).filter(Role.role_id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# UserToken CRUD operations
class CRUDUserToken(CRUDBase[UserToken, UserTokenCreate, UserTokenUpdate]):
    def get_by_token_hash(self, db: Session, token_hash: str) -> Optional[UserToken]:
        """Get a token by its hash"""
        return db.query(UserToken).filter(UserToken.token_hash == token_hash).first()
    
    def get_active_tokens_for_user(self, db: Session, user_id: str) -> List[UserToken]:
        """Get all active tokens for a user"""
        now = now_utc()
        return db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.expired_at > now,
            UserToken.revoked.is_(False)
        ).all()
    
    def revoke_token(self, db: Session, token_id: str) -> Optional[UserToken]:
        """Revoke a token"""
        token = db.query(UserToken).filter(UserToken.id == token_id).first()
        if token:
            token.revoked = True
            token.revoked_at = now_utc()
            db.add(token)
            db.commit()
            db.refresh(token)
        return token
    
    def revoke_all_for_user(self, db: Session, user_id: str) -> int:
        """Revoke all tokens for a user"""
        now = now_utc()
        tokens = db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.revoked.is_(False)
        ).all()
        
        count = 0
        for token in tokens:
            token.revoked = True
            token.revoked_at = now
            db.add(token)
            count += 1
        
        db.commit()
        return count


# UserInfo CRUD operations
class CRUDUserInfo(CRUDBase[UserInfo, UserInfoCreate, UserInfoUpdate]):
    def get(self, db: Session, id: str) -> Optional[UserInfo]:
        """Override to use user_id instead of id"""
        return db.query(UserInfo).filter(UserInfo.user_id == id).first()
    
    def get_by_username(self, db: Session, username: str) -> Optional[UserInfo]:
        """Get a user by username"""
        return db.query(UserInfo).filter(UserInfo.username == username).first()
    
    def get_active_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[UserInfo]:
        """Get active (not deleted) users"""
        return db.query(UserInfo).filter(
            UserInfo.deleted_at.is_(None)
        ).offset(skip).limit(limit).all()
    
    def remove(self, db: Session, *, id: str) -> Optional[UserInfo]:
        """Override to use user_id instead of id"""
        obj = db.query(UserInfo).filter(UserInfo.user_id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# Article CRUD operations
class CRUDArticle(CRUDBase[Article, ArticleCreate, ArticleUpdate]):
    def search_articles(self, db: Session, search_term: str, skip: int = 0, limit: int = 100) -> List[Article]:
        """Search articles by title or content"""
        search_pattern = f"%{search_term}%"
        return db.query(Article).filter(
            or_(
                Article.title.ilike(search_pattern),
                Article.content.ilike(search_pattern),
                Article.summary.ilike(search_pattern)
            ),
            Article.deleted_at.is_(None)
        ).offset(skip).limit(limit).all()
    
    def get_by_author(self, db: Session, author_id: str, skip: int = 0, limit: int = 100) -> List[Article]:
        """Get articles by author (created_by)"""
        return db.query(Article).filter(
            Article.created_by == author_id,
            Article.deleted_at.is_(None)
        ).offset(skip).limit(limit).all()


# Clinic CRUD operations
class CRUDClinic(CRUDBase[Clinic, ClinicCreate, ClinicUpdate]):
    def search_clinics(self, db: Session, search_term: str, skip: int = 0, limit: int = 100) -> List[Clinic]:
        """Search clinics by name, description or location"""
        search_pattern = f"%{search_term}%"
        return db.query(Clinic).filter(
            or_(
                Clinic.name.ilike(search_pattern),
                Clinic.description.ilike(search_pattern),
                Clinic.location.ilike(search_pattern)
            ),
            Clinic.deleted_at.is_(None)
        ).offset(skip).limit(limit).all()


# Report CRUD operations
class CRUDReport(CRUDBase[Report, ReportCreate, ReportUpdate]):
    def search_reports(self, db: Session, search_term: str, skip: int = 0, limit: int = 100) -> List[Report]:
        """Search reports by title or description"""
        search_pattern = f"%{search_term}%"
        return db.query(Report).filter(
            or_(
                Report.title.ilike(search_pattern),
                Report.description.ilike(search_pattern)
            ),
            Report.deleted_at.is_(None)
        ).offset(skip).limit(limit).all()


# Image CRUD operations
class CRUDImage(CRUDBase[Image, ImageCreate, ImageUpdate]):
    def get_by_uploaded_by(self, db: Session, uploaded_by: str, skip: int = 0, limit: int = 100) -> List[Image]:
        """Get images by uploader"""
        return db.query(Image).filter(
            Image.uploaded_by == uploaded_by
        ).offset(skip).limit(limit).all()
    
    def get_by_mime_type(self, db: Session, mime_type: str, skip: int = 0, limit: int = 100) -> List[Image]:
        """Get images by MIME type"""
        return db.query(Image).filter(
            Image.mime_type == mime_type
        ).offset(skip).limit(limit).all()


# ImageUsage CRUD operations
class CRUDImageUsage(CRUDBase[ImageUsage, ImageUsageCreate, ImageUsageUpdate]):
    def get(self, db: Session, id: str) -> Optional[ImageUsage]:
        """Override to use usage field as primary key"""
        return db.query(ImageUsage).filter(ImageUsage.usage == id).first()
    
    def remove(self, db: Session, *, id: str) -> Optional[ImageUsage]:
        """Override to use usage field as primary key"""
        obj = db.query(ImageUsage).filter(ImageUsage.usage == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# ImageMap CRUD operations
class CRUDImageMap(CRUDBase[ImageMap, ImageMapCreate, ImageMapUpdate]):
    def get_by_object(self, db: Session, object_type: str, object_id: str) -> List[ImageMap]:
        """Get image maps by object type and ID"""
        return db.query(ImageMap).filter(
            ImageMap.object_type == object_type,
            ImageMap.object_id == object_id
        ).all()
    
    def get_by_image(self, db: Session, image_id: str) -> List[ImageMap]:
        """Get image maps by image ID"""
        return db.query(ImageMap).filter(
            ImageMap.image_id == image_id
        ).all()
    
    def get_by_object_and_usage(self, db: Session, object_type: str, object_id: str, usage: str) -> Optional[ImageMap]:
        """Get image map by object type, ID and usage"""
        return db.query(ImageMap).filter(
            ImageMap.object_type == object_type,
            ImageMap.object_id == object_id,
            ImageMap.usage == usage
        ).first()
    
    def get_with_images(self, db: Session, object_type: str, object_id: str) -> List[Dict[str, Any]]:
        """Get image maps with corresponding image data for an object"""
        image_maps = db.query(ImageMap).filter(
            ImageMap.object_type == object_type,
            ImageMap.object_id == object_id
        ).all()
        
        result = []
        for image_map in image_maps:
            image = db.query(Image).filter(Image.id == image_map.image_id).first()
            result.append({
                "id": image_map.id,
                "image_id": image_map.image_id,
                "object_type": image_map.object_type,
                "object_id": image_map.object_id,
                "usage": image_map.usage,
                "image": image
            })
        
        return result


# Create instances for each CRUD class to use as singletons
disease = CRUDDisease(Disease)
domain = CRUDDomain(Domain)
disease_domain_crossmap = CRUDDiseaseDomainCrossmap(DiseaseDomainCrossmap)
diagnosis_log = CRUDDiagnosisLog(DiagnosisLog)
diagnosis_log_disease = CRUDDiagnosisLogDisease(DiagnosisLogDisease)
role = CRUDRole(Role)
user_token = CRUDUserToken(UserToken)
user = CRUDUserInfo(UserInfo)
article = CRUDArticle(Article)
clinic = CRUDClinic(Clinic)
report = CRUDReport(Report)
image = CRUDImage(Image)
image_usage = CRUDImageUsage(ImageUsage)
image_map = CRUDImageMap(ImageMap) 