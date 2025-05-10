from enum import Enum

class EntityType(str, Enum):
    DISEASE = 'Disease'
    CAUSE = 'Cause'
    SYMPTOM = 'Symptom'
    TREATMENT = 'Treatment'
    DIAGNOSIS = 'Diagnosis'
    PREVENTION = 'Prevention'
    ANATOMY = 'Anatomy'
    COMPLICATION = 'Complication'
    CONTRAINDICATION = 'Contraindication'

    @classmethod
    def all_types(cls):
        return list(cls)
    
    @classmethod
    def get_type_by_name(cls, name):
        return cls[name]
    
class RelationType(str, Enum):
    HAS_SYMPTOM = 'HAS_SYMPTOM'
    CAUSED_BY = 'CAUSED_BY'
    RISK_FACTOR = 'RISK_FACTOR'
    TREATED_WITH = 'TREATED_WITH'
    DIAGNOSED_BY = 'DIAGNOSED_BY'
    PREVENTED_BY = 'PREVENTED_BY'
    AFFECTS = 'AFFECTS'
    COMPLICATION_OF = 'COMPLICATION_OF'
    CONTRAINDICATES = 'CONTRAINDICATES'
    
    @classmethod
    def all_types(cls):
        return list(cls)
    
    @classmethod
    def get_type_by_name(cls, name):
        return cls[name]
    
class QueryType(str, Enum):
    DISEASE_TREATMENTS = "disease_treatments"
    DISEASE_SYMPTOMS = "disease_symptoms"
    DISEASE_CAUSES = "disease_causes"
    DISEASES_BY_ANATOMY = "diseases_by_anatomy"
    DISEASES_BY_SYMPTOM = "diseases_by_symptom"
    SIMILAR_DISEASES = "similar_diseases"
    
    @classmethod
    def all_types(cls):
        return list(cls)
    
    @classmethod
    def get_type_by_name(cls, name):
        return cls[name] 