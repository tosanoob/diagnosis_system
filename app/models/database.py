from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# Base models with shared fields
class BaseModelWithTimestamps(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

class BaseModelWithAudit(BaseModelWithTimestamps):
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None

# Disease models
class DiseaseBase(BaseModel):
    label: str
    domain_id: str
    description: Optional[str] = None
    included_in_diagnosis: bool = True
    article_id: Optional[str] = None

class DiseaseCreate(DiseaseBase):
    pass

class DiseaseUpdate(DiseaseBase):
    label: Optional[str] = None
    domain_id: Optional[str] = None
    description: Optional[str] = None
    included_in_diagnosis: Optional[bool] = None
    article_id: Optional[str] = None

class Disease(DiseaseBase, BaseModelWithAudit):
    id: str
    
    class Config:
        from_attributes = True

# Domain models
class DomainBase(BaseModel):
    domain: str
    description: Optional[str] = None

class DomainCreate(DomainBase):
    created_by: Optional[str] = None

class DomainUpdate(DomainBase):
    domain: Optional[str] = None
    description: Optional[str] = None
    updated_by: Optional[str] = None
    
class Domain(DomainBase, BaseModelWithAudit):
    id: str
    
    class Config:
        from_attributes = True

# DiseaseDomainCrossmap models
class DiseaseDomainCrossmapBase(BaseModel):
    disease_id_1: str
    domain_id_1: str
    disease_id_2: str
    domain_id_2: str

class DiseaseDomainCrossmapCreate(DiseaseDomainCrossmapBase):
    pass

class DiseaseDomainCrossmapUpdate(DiseaseDomainCrossmapBase):
    disease_id_1: Optional[str] = None
    domain_id_1: Optional[str] = None
    disease_id_2: Optional[str] = None
    domain_id_2: Optional[str] = None

class DiseaseDomainCrossmap(DiseaseDomainCrossmapBase):
    id: str
    
    class Config:
        from_attributes = True

class DiseaseDomainCrossmapBatchCreate(BaseModel):
    crossmaps: List[DiseaseDomainCrossmapCreate]

class StandardDomainCrossmapBatchUpdate(BaseModel):
    """Model để tạo batch ánh xạ từ domain STANDARD sang domain khác"""
    target_domain_id: str
    crossmaps_lite: List[Dict[str, str]]
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "target_domain_id": "domain-id-1",
                    "crossmaps_lite": [
                        {"standard_disease_id": "standard-disease-id-1", "target_disease_id": "target-disease-id-1"},
                        {"standard_disease_id": "standard-disease-id-2", "target_disease_id": "target-disease-id-2"}
                    ]
                }
            ]
        }
    }

# DiagnosisLog models
class DiagnosisLogBase(BaseModel):
    image_content: Optional[str] = None
    text_content: Optional[str] = None
    result_text: Optional[str] = None
    result_reasoning: Optional[str] = None

class DiagnosisLogCreate(DiagnosisLogBase):
    pass

class DiagnosisLogUpdate(DiagnosisLogBase):
    image_content: Optional[str] = None
    text_content: Optional[str] = None
    result_text: Optional[str] = None
    result_reasoning: Optional[str] = None

class DiagnosisLog(DiagnosisLogBase, BaseModelWithTimestamps):
    id: str
    diseases: Optional[List[str]] = None
    
    class Config:
        from_attributes = True

# DiagnosisLogDisease models
class DiagnosisLogDiseaseBase(BaseModel):
    diagnosis_log_id: str
    disease_id: str

class DiagnosisLogDiseaseCreate(DiagnosisLogDiseaseBase):
    pass

class DiagnosisLogDiseaseUpdate(DiagnosisLogDiseaseBase):
    diagnosis_log_id: Optional[str] = None
    disease_id: Optional[str] = None

class DiagnosisLogDisease(DiagnosisLogDiseaseBase):
    id: str
    
    class Config:
        from_attributes = True

# Role models
class RoleBase(BaseModel):
    role: str

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    role: Optional[str] = None

class Role(RoleBase):
    role_id: str
    
    class Config:
        from_attributes = True

# UserToken models
class UserTokenBase(BaseModel):
    user_id: str
    token_hash: str
    expired_at: Optional[datetime] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None

class UserTokenCreate(UserTokenBase):
    pass

class UserTokenUpdate(UserTokenBase):
    user_id: Optional[str] = None
    token_hash: Optional[str] = None
    expired_at: Optional[datetime] = None
    revoked: Optional[bool] = None
    revoked_at: Optional[datetime] = None

class UserToken(UserTokenBase, BaseModelWithTimestamps):
    id: str
    
    class Config:
        from_attributes = True

# UserInfo models
class UserInfoBase(BaseModel):
    username: str
    hashpass: str
    role_id: Optional[str] = None

class UserInfoCreate(UserInfoBase):
    pass

class UserInfoUpdate(UserInfoBase):
    username: Optional[str] = None
    hashpass: Optional[str] = None
    role_id: Optional[str] = None

class UserInfo(UserInfoBase, BaseModelWithTimestamps):
    user_id: str
    
    class Config:
        from_attributes = True

# Article models
class ArticleBase(BaseModel):
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(ArticleBase):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None

class Article(ArticleBase, BaseModelWithAudit):
    id: str
    
    class Config:
        from_attributes = True

# Clinic models
class ClinicBase(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None

class ClinicCreate(ClinicBase):
    pass

class ClinicUpdate(ClinicBase):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None

class Clinic(ClinicBase, BaseModelWithAudit):
    id: str
    
    class Config:
        from_attributes = True

# Report models
class ReportBase(BaseModel):
    title: str
    description: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportUpdate(ReportBase):
    title: Optional[str] = None
    description: Optional[str] = None

class Report(ReportBase, BaseModelWithTimestamps):
    id: str
    
    class Config:
        from_attributes = True

# Image models
class ImageBase(BaseModel):
    base_url: str
    rel_path: str
    mime_type: str
    uploaded_by: Optional[str] = None

class ImageCreate(ImageBase):
    pass

class ImageUpdate(ImageBase):
    base_url: Optional[str] = None
    rel_path: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[str] = None

class Image(ImageBase):
    id: str
    uploaded_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ImageUsage models
class ImageUsageBase(BaseModel):
    usage: str
    description: Optional[str] = None

class ImageUsageCreate(ImageUsageBase):
    pass

class ImageUsageUpdate(ImageUsageBase):
    description: Optional[str] = None

class ImageUsage(ImageUsageBase):
    class Config:
        from_attributes = True

# ImageMap models
class ImageMapBase(BaseModel):
    image_id: str
    object_type: str
    object_id: str
    usage: str

class ImageMapCreate(ImageMapBase):
    pass

class ImageMapUpdate(ImageMapBase):
    image_id: Optional[str] = None
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    usage: Optional[str] = None

class ImageMapWithImage(ImageMapBase):
    id: str
    image: Optional[Image] = None
    
    class Config:
        from_attributes = True

class ImageMap(ImageMapBase):
    id: str
    
    class Config:
        from_attributes = True 